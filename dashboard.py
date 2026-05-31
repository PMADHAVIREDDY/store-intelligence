import requests
import time
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich import box
from datetime import datetime

STORE_ID = "STORE_BRIGADE_ROAD"
API = "http://localhost:8000"

def get_data(endpoint):
    try:
        return requests.get(f"{API}{endpoint}", timeout=3).json()
    except:
        return None

def build_dashboard():
    metrics = get_data(f"/stores/{STORE_ID}/metrics")
    funnel = get_data(f"/stores/{STORE_ID}/funnel")
    anomalies = get_data(f"/stores/{STORE_ID}/anomalies")

    table = Table(box=box.ROUNDED, title="Purplle Store Intelligence - Brigade Road")
    table.add_column("Metric", style="cyan", width=30)
    table.add_column("Value", style="green", width=40)

    if metrics:
        table.add_row("Unique Visitors Today", str(metrics.get("unique_visitors", 0)))
        conv = metrics.get("conversion_rate", 0)
        table.add_row("Conversion Rate", f"{conv*100:.1f}%")
        table.add_row("Queue Depth", str(metrics.get("queue_depth", 0)))
        table.add_row("Abandonment Rate", f"{metrics.get('abandonment_rate',0)*100:.1f}%")
        table.add_section()
        for zone in metrics.get("avg_dwell_per_zone", []):
            table.add_row(
                f"Zone: {zone['zone_id']}",
                f"Avg dwell: {zone['avg_dwell_ms']/1000:.0f}s | Visits: {zone['visit_count']}"
            )

    if funnel:
        table.add_section()
        for stage in funnel.get("stages", []):
            table.add_row(
                f"Funnel: {stage['stage']}",
                f"{stage['count']} visitors | {stage['dropoff_pct']}% dropoff"
            )

    if anomalies and anomalies.get("anomalies"):
        table.add_section()
        for a in anomalies["anomalies"]:
            table.add_row(
                f"ALERT: {a['anomaly_type']}",
                f"[{a['severity']}] {a['suggested_action']}"
            )
    else:
        table.add_section()
        table.add_row("Anomalies", "None detected")

    table.add_section()
    table.add_row("Last Updated", datetime.now().strftime("%H:%M:%S"))
    return Panel(table, border_style="blue")

with Live(build_dashboard(), refresh_per_second=0.5, screen=True) as live:
    while True:
        time.sleep(2)
        live.update(build_dashboard())
