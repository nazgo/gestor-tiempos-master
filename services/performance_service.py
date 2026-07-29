from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple


class PerformanceService:
    """Construye indicadores deportivos sin modificar la base de datos.

    Los puntajes son indicadores internos de actividad y progreso. No sustituyen
    una evaluación técnica del entrenador.
    """

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
        text = str(value).strip()[:10]
        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return None

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

    @staticmethod
    def _name_key(value: str) -> str:
        return " ".join((value or "").lower().split())

    def _load_data(self):
        nadadores = self.gestor_nadadores.listar_nadadores()
        tiempos = self._fetch("""
            SELECT id, nombre_nadador, estilo, distancia, piscina, tiempo,
                   tiempo_segundos, fecha, competencia_id, genero, categoria
            FROM tiempos
            WHERE fecha IS NOT NULL
            ORDER BY fecha ASC, id ASC
        """)
        competencias = self._fetch("""
            SELECT id, nombre, fecha, lugar, tipo_piscina, estado
            FROM competencias
            WHERE fecha IS NOT NULL
            ORDER BY fecha ASC
        """)
        try:
            asistencias = self._fetch("""
                SELECT nadador_id, competencia_id, estado
                FROM asistencia_competencias
            """)
        except Exception:
            asistencias = []
        return nadadores, tiempos, competencias, asistencias

    def build_center(self) -> Dict[str, Any]:
        today = date.today()
        current_year = today.year
        cutoff_active = today - timedelta(days=120)
        cutoff_recent = today - timedelta(days=90)
        cutoff_previous = today - timedelta(days=180)
        nadadores, tiempos, competencias, asistencias = self._load_data()

        athlete_by_name = {
            self._name_key(f"{n.get('nombre', '')} {n.get('apellido', '')}"): n
            for n in nadadores
        }
        athlete_times: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        month_counts = Counter()
        style_year_counts = Counter()

        for t in tiempos:
            t["fecha_obj"] = self._as_date(t.get("fecha"))
            key = self._name_key(t.get("nombre_nadador", ""))
            athlete_times[key].append(t)
            if t["fecha_obj"] and t["fecha_obj"].year == current_year:
                month_counts[t["fecha_obj"].month] += 1
                style_year_counts[t.get("estilo") or "Sin estilo"] += 1

        active_names = {
            key for key, rows in athlete_times.items()
            if any(row["fecha_obj"] and row["fecha_obj"] >= cutoff_active for row in rows)
        }

        pb_events = self._detect_personal_bests(tiempos)
        recent_pbs = [pb for pb in pb_events if pb["fecha"] >= cutoff_recent]
        scores = []
        for key, athlete in athlete_by_name.items():
            rows = athlete_times.get(key, [])
            scores.append(self._score_athlete(athlete, rows, pb_events, asistencias, today))
        scores.sort(key=lambda item: (-item["score"], -item["improvement_pct"], item["nombre"]))

        completed_year = [c for c in competencias if self._as_date(c.get("fecha")) and self._as_date(c.get("fecha")).year == current_year and self._as_date(c.get("fecha")) <= today]
        upcoming = [c for c in competencias if self._as_date(c.get("fecha")) and self._as_date(c.get("fecha")) >= today]
        upcoming.sort(key=lambda c: self._as_date(c.get("fecha")))

        attendance_rate = self._attendance_rate(asistencias)
        active_rate = round((len(active_names) / len(nadadores) * 100), 1) if nadadores else 0
        pb_rate = min(100.0, len(recent_pbs) * 8.0)
        competition_rate = min(100.0, len(completed_year) * 12.5)
        club_score = round(active_rate * .40 + attendance_rate * .25 + pb_rate * .20 + competition_rate * .15)

        heatmap = self._build_heatmap(tiempos, today)
        trends = self._style_trends(tiempos, today)
        inactive = self._inactive_athletes(nadadores, athlete_times, today)
        insights = self._build_insights(active_rate, recent_pbs, trends, inactive, scores)

        labels = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        next_comp = upcoming[0] if upcoming else None
        if next_comp:
            next_date = self._as_date(next_comp.get("fecha"))
            next_comp = dict(next_comp)
            next_comp["dias"] = max((next_date - today).days, 0) if next_date else None

        return {
            "generated_at": datetime.now(),
            "club": {
                "score": max(0, min(100, club_score)),
                "status": self._score_status(club_score),
                "active_rate": active_rate,
                "attendance_rate": attendance_rate,
                "active_athletes": len(active_names),
                "total_athletes": len(nadadores),
                "recent_pbs": len(recent_pbs),
                "competitions_year": len(completed_year),
            },
            "top_performers": scores[:6],
            "recent_pbs": sorted(recent_pbs, key=lambda x: x["fecha"], reverse=True)[:6],
            "inactive": inactive[:6],
            "insights": insights,
            "heatmap": heatmap,
            "trends": trends,
            "monthly": {"labels": labels, "values": [month_counts.get(i, 0) for i in range(1, 13)]},
            "next_competition": next_comp,
        }

    def _detect_personal_bests(self, tiempos: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        best: Dict[Tuple[str, str, int, str], float] = {}
        events = []
        for row in tiempos:
            fecha = row.get("fecha_obj") or self._as_date(row.get("fecha"))
            try:
                seconds = float(row.get("tiempo_segundos"))
            except (TypeError, ValueError):
                continue
            key = (
                self._name_key(row.get("nombre_nadador", "")),
                row.get("estilo") or "Sin estilo",
                int(row.get("distancia") or 0),
                row.get("piscina") or "Sin piscina",
            )
            previous = best.get(key)
            if previous is None or seconds < previous:
                improvement = ((previous - seconds) / previous * 100) if previous else 0.0
                events.append({
                    "nombre": row.get("nombre_nadador") or "Nadador",
                    "estilo": key[1], "distancia": key[2], "piscina": key[3],
                    "tiempo": row.get("tiempo"), "segundos": seconds,
                    "fecha": fecha, "improvement_pct": round(improvement, 2),
                })
                best[key] = seconds
        return events

    def _score_athlete(self, athlete, rows, pb_events, asistencias, today):
        name = f"{athlete.get('nombre', '')} {athlete.get('apellido', '')}".strip()
        key = self._name_key(name)
        dates = sorted([r["fecha_obj"] for r in rows if r.get("fecha_obj")])
        last_date = dates[-1] if dates else None
        days_inactive = (today - last_date).days if last_date else 999
        recency = max(0, 100 - days_inactive * 0.75)
        competition_ids = {r.get("competencia_id") for r in rows if r.get("competencia_id")}
        participation = min(100, len(competition_ids) * 16.7)
        recent_rows = [r for r in rows if r.get("fecha_obj") and r["fecha_obj"] >= today - timedelta(days=365)]
        consistency = min(100, len(recent_rows) * 4)
        pbs = [p for p in pb_events if self._name_key(p["nombre"]) == key and p["fecha"] and p["fecha"] >= today - timedelta(days=365)]
        improvement_values = [p["improvement_pct"] for p in pbs if p["improvement_pct"] > 0]
        improvement_pct = round(sum(improvement_values) / len(improvement_values), 2) if improvement_values else 0
        progress = min(100, len(pbs) * 12 + improvement_pct * 5)
        score = round(recency * .25 + participation * .25 + progress * .30 + consistency * .20)
        return {
            "id": athlete.get("id"), "nombre": name,
            "categoria": athlete.get("categoria_master") or "Sin categoría",
            "genero": athlete.get("genero") or "",
            "score": max(0, min(100, score)),
            "status": self._score_status(score),
            "improvement_pct": improvement_pct,
            "pbs": len(pbs), "records": len(rows),
            "last_activity": last_date, "days_inactive": days_inactive,
        }

    @staticmethod
    def _attendance_rate(rows):
        if not rows:
            return 0.0
        positive = {"ASISTIO", "ASISTIÓ", "SI", "SÍ", "PRESENTE", "CONFIRMADO"}
        registered = [str(r.get("estado") or "").upper() for r in rows if str(r.get("estado") or "").upper() != "SIN_REGISTRO"]
        return round(sum(state in positive for state in registered) / len(registered) * 100, 1) if registered else 0.0

    def _build_heatmap(self, tiempos, today):
        start = today - timedelta(days=83)
        counts = Counter(t["fecha_obj"] for t in tiempos if t.get("fecha_obj") and t["fecha_obj"] >= start)
        max_count = max(counts.values(), default=1)
        days = []
        for offset in range(84):
            day = start + timedelta(days=offset)
            count = counts.get(day, 0)
            level = 0 if count == 0 else min(4, max(1, round(count / max_count * 4)))
            days.append({"date": day.isoformat(), "label": day.strftime("%d/%m"), "count": count, "level": level})
        return days

    def _style_trends(self, tiempos, today):
        recent_start = today - timedelta(days=90)
        previous_start = today - timedelta(days=180)
        recent, previous = Counter(), Counter()
        for row in tiempos:
            d = row.get("fecha_obj")
            style = row.get("estilo") or "Sin estilo"
            if d and d >= recent_start:
                recent[style] += 1
            elif d and d >= previous_start:
                previous[style] += 1
        result = []
        for style in sorted(set(recent) | set(previous), key=lambda s: recent[s], reverse=True):
            old, new = previous[style], recent[style]
            change = round((new - old) / old * 100, 1) if old else (100.0 if new else 0.0)
            result.append({"style": style, "recent": new, "previous": old, "change": change, "direction": "up" if change > 5 else "down" if change < -5 else "flat"})
        return result[:5]

    def _inactive_athletes(self, nadadores, athlete_times, today):
        result = []
        for n in nadadores:
            name = f"{n.get('nombre', '')} {n.get('apellido', '')}".strip()
            dates = [r["fecha_obj"] for r in athlete_times.get(self._name_key(name), []) if r.get("fecha_obj")]
            last = max(dates) if dates else None
            days = (today - last).days if last else None
            if days is None or days >= 60:
                result.append({"id": n.get("id"), "nombre": name, "categoria": n.get("categoria_master") or "", "last_activity": last, "days": days})
        return sorted(result, key=lambda x: (x["days"] is None, x["days"] or 9999), reverse=True)

    def _build_insights(self, active_rate, recent_pbs, trends, inactive, scores):
        items = []
        items.append({"type": "success" if active_rate >= 70 else "warning", "icon": "fa-person-swimming", "text": f"El {active_rate:.0f}% del plantel registró actividad durante los últimos 120 días."})
        if recent_pbs:
            items.append({"type": "success", "icon": "fa-medal", "text": f"Se detectaron {len(recent_pbs)} nuevas mejores marcas en los últimos 90 días."})
        else:
            items.append({"type": "neutral", "icon": "fa-stopwatch", "text": "No se detectaron nuevas mejores marcas en los últimos 90 días."})
        if trends:
            leader = max(trends, key=lambda x: x["change"])
            items.append({"type": "info", "icon": "fa-chart-line", "text": f"{leader['style']} es el estilo con mayor crecimiento reciente ({leader['change']:+.0f}%)."})
        if inactive:
            items.append({"type": "warning", "icon": "fa-triangle-exclamation", "text": f"Hay {len(inactive)} nadadores con 60 días o más sin registros competitivos."})
        if scores:
            items.append({"type": "info", "icon": "fa-star", "text": f"{scores[0]['nombre']} lidera el Performance Score con {scores[0]['score']} puntos."})
        return items[:5]

    @staticmethod
    def _score_status(score):
        if score >= 85: return "Excelente"
        if score >= 70: return "Muy bueno"
        if score >= 55: return "En progreso"
        if score >= 35: return "Atención"
        return "Sin actividad"
