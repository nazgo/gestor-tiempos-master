from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


class CoachService:
    """Herramientas de apoyo para comparar nadadores y detectar focos de atención."""

    def __init__(self, gestor_tiempos, gestor_nadadores):
        self.gestor_tiempos = gestor_tiempos
        self.gestor_nadadores = gestor_nadadores

    @staticmethod
    def _as_date(value: Any) -> Optional[date]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _name_key(value: str) -> str:
        return " ".join((value or "").lower().split())

    @staticmethod
    def _row_to_dict(row: Any, cursor=None) -> Dict[str, Any]:
        if row is None:
            return {}
        if hasattr(row, "keys"):
            return dict(row)
        if cursor is not None and getattr(cursor, "description", None):
            return dict(zip([item[0] for item in cursor.description], row))
        return dict(row)

    def _fetch(self, query: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        cursor = self.gestor_tiempos._execute(query, params, commit=False)
        return [self._row_to_dict(row, cursor) for row in cursor.fetchall()]

    def athlete_options(self) -> List[Dict[str, Any]]:
        athletes = self.gestor_nadadores.listar_nadadores()
        result = []
        for athlete in athletes:
            full_name = f"{athlete.get('nombre', '')} {athlete.get('apellido', '')}".strip()
            result.append({
                "id": athlete.get("id"),
                "nombre": full_name,
                "categoria": athlete.get("categoria_master") or "Sin categoría",
                "genero": athlete.get("genero") or "",
            })
        return sorted(result, key=lambda x: x["nombre"].lower())

    def build(self, athlete_a_id: Optional[int] = None, athlete_b_id: Optional[int] = None) -> Dict[str, Any]:
        athletes = self.athlete_options()
        comparison = None
        if athlete_a_id and athlete_b_id and athlete_a_id != athlete_b_id:
            comparison = self.compare(athlete_a_id, athlete_b_id)

        return {
            "athletes": athletes,
            "selected_a": athlete_a_id,
            "selected_b": athlete_b_id,
            "comparison": comparison,
            "attention": self._attention_list(),
            "generated_at": datetime.now(),
        }

    def compare(self, athlete_a_id: int, athlete_b_id: int) -> Dict[str, Any]:
        athlete_map = {a["id"]: a for a in self.athlete_options()}
        athlete_a = athlete_map.get(athlete_a_id)
        athlete_b = athlete_map.get(athlete_b_id)
        if not athlete_a or not athlete_b:
            return None

        rows = self._fetch("""
            SELECT nombre_nadador, estilo, distancia, piscina, tiempo,
                   tiempo_segundos, fecha, competencia_id
            FROM tiempos
            WHERE fecha IS NOT NULL
            ORDER BY fecha ASC, id ASC
        """)
        by_name = defaultdict(list)
        for row in rows:
            row["fecha_obj"] = self._as_date(row.get("fecha"))
            by_name[self._name_key(row.get("nombre_nadador", ""))].append(row)

        data_a = self._athlete_metrics(athlete_a, by_name.get(self._name_key(athlete_a["nombre"]), []))
        data_b = self._athlete_metrics(athlete_b, by_name.get(self._name_key(athlete_b["nombre"]), []))

        common_events = []
        event_keys = sorted(set(data_a["best_by_event"]) & set(data_b["best_by_event"]))
        for key in event_keys:
            a = data_a["best_by_event"][key]
            b = data_b["best_by_event"][key]
            winner = "a" if a["seconds"] < b["seconds"] else "b" if b["seconds"] < a["seconds"] else "tie"
            common_events.append({
                "event": f"{key[1]} m {key[0]} · Piscina {key[2]}",
                "a": a,
                "b": b,
                "difference": round(abs(a["seconds"] - b["seconds"]), 2),
                "winner": winner,
            })

        radar_labels = ["Actividad", "Constancia", "Progreso", "Competencias", "Variedad"]
        return {
            "a": data_a,
            "b": data_b,
            "common_events": common_events[:12],
            "radar": {
                "labels": radar_labels,
                "a": [data_a["scores"][k] for k in ["activity", "consistency", "progress", "competitions", "variety"]],
                "b": [data_b["scores"][k] for k in ["activity", "consistency", "progress", "competitions", "variety"]],
            },
            "verdict": self._verdict(data_a, data_b),
        }

    def _athlete_metrics(self, athlete: Dict[str, Any], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        today = date.today()
        valid = []
        for row in rows:
            try:
                seconds = float(row.get("tiempo_segundos"))
            except (TypeError, ValueError):
                continue
            if seconds <= 0:
                continue
            item = dict(row)
            item["seconds"] = seconds
            valid.append(item)

        dates = sorted([r["fecha_obj"] for r in valid if r.get("fecha_obj")])
        last_date = dates[-1] if dates else None
        days_inactive = (today - last_date).days if last_date else 999
        recent = [r for r in valid if r.get("fecha_obj") and r["fecha_obj"] >= today - timedelta(days=365)]
        competitions = {r.get("competencia_id") for r in valid if r.get("competencia_id")}
        styles = {r.get("estilo") for r in valid if r.get("estilo")}

        best_by_event = {}
        progress_values = []
        grouped = defaultdict(list)
        for row in valid:
            key = (row.get("estilo") or "Sin estilo", int(row.get("distancia") or 0), row.get("piscina") or "-")
            grouped[key].append(row)
        for key, event_rows in grouped.items():
            event_rows.sort(key=lambda x: (x.get("fecha_obj") or date.min, x.get("seconds")))
            best = min(event_rows, key=lambda x: x["seconds"])
            first = event_rows[0]
            improvement = ((first["seconds"] - best["seconds"]) / first["seconds"] * 100) if first["seconds"] else 0
            if improvement > 0:
                progress_values.append(improvement)
            best_by_event[key] = {
                "time": best.get("tiempo") or self._format_seconds(best["seconds"]),
                "seconds": round(best["seconds"], 2),
                "date": best.get("fecha_obj"),
                "improvement": round(max(0, improvement), 2),
            }

        avg_progress = round(sum(progress_values) / len(progress_values), 2) if progress_values else 0
        scores = {
            "activity": max(0, min(100, round(100 - days_inactive * .8))),
            "consistency": min(100, len(recent) * 4),
            "progress": min(100, round(avg_progress * 12 + len(progress_values) * 4)),
            "competitions": min(100, len(competitions) * 15),
            "variety": min(100, len(styles) * 20),
        }
        overall = round(sum(scores.values()) / len(scores))

        return {
            **athlete,
            "records": len(valid),
            "events": len(best_by_event),
            "competitions": len(competitions),
            "styles": len(styles),
            "last_activity": last_date,
            "days_inactive": days_inactive,
            "average_progress": avg_progress,
            "overall": overall,
            "scores": scores,
            "best_by_event": best_by_event,
            "season_activity": self._season_activity(valid),
        }

    @staticmethod
    def _season_activity(rows: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        counter = Counter(r["fecha_obj"].year for r in rows if r.get("fecha_obj"))
        years = sorted(counter.keys())[-5:]
        return {"labels": [str(y) for y in years], "values": [counter[y] for y in years]}

    def _attention_list(self) -> List[Dict[str, Any]]:
        today = date.today()
        athletes = self.athlete_options()
        rows = self._fetch("SELECT nombre_nadador, fecha FROM tiempos WHERE fecha IS NOT NULL")
        last_by_name = {}
        for row in rows:
            key = self._name_key(row.get("nombre_nadador", ""))
            d = self._as_date(row.get("fecha"))
            if d and (key not in last_by_name or d > last_by_name[key]):
                last_by_name[key] = d
        result = []
        for athlete in athletes:
            last = last_by_name.get(self._name_key(athlete["nombre"]))
            days = (today - last).days if last else None
            if days is None or days >= 60:
                result.append({**athlete, "last_activity": last, "days": days})
        result.sort(key=lambda x: (x["days"] is not None, -(x["days"] or 9999)))
        return result[:8]

    @staticmethod
    def _verdict(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, str]:
        diff = a["overall"] - b["overall"]
        if abs(diff) <= 3:
            return {"title": "Comparación equilibrada", "text": "Ambos nadadores muestran un nivel global muy similar en los indicadores analizados."}
        leader, other = (a, b) if diff > 0 else (b, a)
        strongest = max(leader["scores"], key=leader["scores"].get)
        labels = {"activity": "actividad reciente", "consistency": "constancia", "progress": "progreso", "competitions": "participación competitiva", "variety": "variedad de estilos"}
        return {"title": f"{leader['nombre']} lidera la comparación", "text": f"Su principal fortaleza relativa es {labels[strongest]}. La diferencia global es de {abs(diff)} puntos."}

    @staticmethod
    def _format_seconds(seconds: float) -> str:
        minutes = int(seconds // 60)
        rest = seconds - minutes * 60
        return f"{minutes}:{rest:05.2f}" if minutes else f"{rest:.2f}"
