"""Bambuddy MCP Server - Control and monitor Bambu Lab 3D printers via Claude.

This MCP server provides tools for monitoring printer status, managing print
queues, browsing archives, and controlling printers through the Bambuddy REST API.

Configuration via environment variables:
    BAMBUDDY_URL     - Base URL of Bambuddy server (default: http://localhost:8000)
    BAMBUDDY_API_KEY - API key for authentication (optional if auth is disabled)
"""

import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from mcp_server.client import BambuddyAPIError, BambuddyClient

# Logging must go to stderr for stdio transport
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("bambuddy-mcp")

mcp = FastMCP(
    "bambuddy",
    instructions="Control and monitor Bambu Lab 3D printers through Bambuddy. "
    "Use list_printers first to discover available printer IDs.",
)

_client: BambuddyClient | None = None


def get_client() -> BambuddyClient:
    global _client
    if _client is None:
        _client = BambuddyClient()
    return _client


def _format_error(e: Exception) -> str:
    if isinstance(e, BambuddyAPIError):
        if e.status_code == 404:
            return f"Not found: {e.detail}"
        if e.status_code == 400:
            return f"Invalid request: {e.detail}"
        if e.status_code == 401:
            return "Authentication failed. Check that BAMBUDDY_API_KEY is set correctly."
        if e.status_code == 403:
            return f"Permission denied: {e.detail}"
        return f"API error (HTTP {e.status_code}): {e.detail}"
    if "ConnectError" in type(e).__name__ or "ConnectionRefused" in str(e):
        url = get_client().base_url
        return f"Cannot connect to Bambuddy at {url}. Ensure the server is running."
    if "ReadTimeout" in type(e).__name__ or "TimeoutException" in type(e).__name__:
        return "Request timed out. The Bambuddy server may be busy."
    return f"Unexpected error: {e}"


def _fmt_time(seconds: int | float | None) -> str:
    if seconds is None:
        return "N/A"
    s = int(seconds)
    h, remainder = divmod(s, 3600)
    m, sec = divmod(remainder, 60)
    if h > 0:
        return f"{h}h {m}m"
    if m > 0:
        return f"{m}m {sec}s"
    return f"{sec}s"


def _fmt_temp(temps: dict | None, key: str) -> str:
    if not temps or key not in temps:
        return "N/A"
    val = temps[key]
    if isinstance(val, (int, float)):
        return f"{val:.1f}°C"
    return str(val)


# ============================================================
# TOOLS: Printer Status & Info
# ============================================================


@mcp.tool()
async def list_printers() -> str:
    """List all configured Bambu Lab printers.

    Returns name, model, connection status, and ID for each printer.
    Use this first to discover available printer IDs for other commands.
    """
    try:
        printers = await get_client().get("/printers/")
        if not printers:
            return "No printers configured in Bambuddy."
        lines = []
        for p in printers:
            status = "active" if p.get("is_active") else "inactive"
            location = f" ({p['location']})" if p.get("location") else ""
            model = p.get("model", "unknown")
            lines.append(
                f"- **{p['name']}** (ID: {p['id']}) - {model} [{status}]{location}"
            )
        return "## Configured Printers\n" + "\n".join(lines)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_printer_status(printer_id: int) -> str:
    """Get comprehensive real-time status of a specific printer.

    Includes temperatures, print progress, AMS filament data, errors,
    fan speeds, and more. Use list_printers first to find printer IDs.

    Args:
        printer_id: Printer ID (use list_printers to find IDs)
    """
    try:
        s = await get_client().get(f"/printers/{printer_id}/status")
        lines = [f"## {s.get('name', 'Printer')} (ID: {printer_id})"]

        # Connection & state
        connected = s.get("connected", False)
        lines.append(f"**Connected:** {'Yes' if connected else 'No'}")
        if not connected:
            return "\n".join(lines)

        state = s.get("state", "UNKNOWN")
        lines.append(f"**State:** {state}")

        # Print progress
        if s.get("current_print"):
            lines.append(f"\n### Current Print")
            lines.append(f"- **File:** {s.get('subtask_name') or s.get('current_print')}")
            progress = s.get("progress")
            if progress is not None:
                lines.append(f"- **Progress:** {progress:.1f}%")
            remaining = s.get("remaining_time")
            if remaining is not None:
                lines.append(f"- **Remaining:** {_fmt_time(remaining * 60)}")
            layer = s.get("layer_num")
            total_layers = s.get("total_layers")
            if layer is not None and total_layers:
                lines.append(f"- **Layer:** {layer}/{total_layers}")
            speed_names = {1: "Silent", 2: "Standard", 3: "Sport", 4: "Ludicrous"}
            speed = speed_names.get(s.get("speed_level", 2), str(s.get("speed_level")))
            lines.append(f"- **Speed:** {speed}")

        # Temperatures
        temps = s.get("temperatures")
        if temps:
            lines.append(f"\n### Temperatures")
            lines.append(f"- **Nozzle:** {_fmt_temp(temps, 'nozzle')} (target: {_fmt_temp(temps, 'nozzle_target')})")
            lines.append(f"- **Bed:** {_fmt_temp(temps, 'bed')} (target: {_fmt_temp(temps, 'bed_target')})")
            if temps.get("chamber") is not None:
                lines.append(f"- **Chamber:** {_fmt_temp(temps, 'chamber')}")

        # AMS
        ams_units = s.get("ams", [])
        if ams_units:
            lines.append(f"\n### AMS Filament")
            for unit in ams_units:
                unit_type = "AMS-HT" if unit.get("is_ams_ht") else "AMS"
                humidity = unit.get("humidity")
                hum_str = f" (humidity: {humidity}%)" if humidity is not None else ""
                lines.append(f"**{unit_type} #{unit.get('id', '?')}{hum_str}:**")
                for tray in unit.get("tray", []):
                    color = tray.get("tray_color", "")
                    ftype = tray.get("tray_type", "empty")
                    brand = tray.get("tray_sub_brands", "")
                    remain = tray.get("remain", 0)
                    name = f"{brand} {ftype}" if brand else ftype
                    lines.append(f"  - Slot {tray.get('id', '?')}: {name} ({remain}% remaining) #{color}")

        # External spool
        vt = s.get("vt_tray")
        if vt and vt.get("tray_type"):
            ftype = vt.get("tray_type", "")
            brand = vt.get("tray_sub_brands", "")
            name = f"{brand} {ftype}" if brand else ftype
            lines.append(f"- **External spool:** {name}")

        # HMS errors
        errors = s.get("hms_errors", [])
        if errors:
            lines.append(f"\n### HMS Errors")
            severity_map = {1: "FATAL", 2: "SERIOUS", 3: "WARNING", 4: "INFO"}
            for err in errors:
                sev = severity_map.get(err.get("severity", 4), "UNKNOWN")
                lines.append(f"- [{sev}] Code: {err.get('code', 'N/A')} (module: {err.get('module', 'N/A')})")

        # Light & fans
        light = s.get("chamber_light", False)
        lines.append(f"\n**Chamber light:** {'ON' if light else 'OFF'}")

        fw = s.get("firmware_version")
        if fw:
            lines.append(f"**Firmware:** {fw}")

        wifi = s.get("wifi_signal")
        if wifi is not None:
            lines.append(f"**WiFi signal:** {wifi} dBm")

        return "\n".join(lines)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_system_info() -> str:
    """Get Bambuddy system information.

    Returns app version, database statistics, connected printers summary,
    disk usage, and host system metrics.
    """
    try:
        info = await get_client().get("/system/info")
        return f"## Bambuddy System Info\n```json\n{json.dumps(info, indent=2, ensure_ascii=False)}\n```"
    except Exception as e:
        return _format_error(e)


# ============================================================
# TOOLS: Print Control
# ============================================================


@mcp.tool()
async def pause_print(printer_id: int) -> str:
    """Pause the active print job on a printer.

    The print can be resumed later with the resume_print tool.

    Args:
        printer_id: Printer ID (use list_printers to find IDs)
    """
    try:
        result = await get_client().post(f"/printers/{printer_id}/print/pause")
        return f"Print paused on printer {printer_id}."
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def resume_print(printer_id: int) -> str:
    """Resume a paused print job on a printer.

    Args:
        printer_id: Printer ID (use list_printers to find IDs)
    """
    try:
        result = await get_client().post(f"/printers/{printer_id}/print/resume")
        return f"Print resumed on printer {printer_id}."
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def stop_print(printer_id: int) -> str:
    """Stop and cancel the active print job on a printer.

    WARNING: This cannot be undone. The print must be restarted from the beginning.

    Args:
        printer_id: Printer ID (use list_printers to find IDs)
    """
    try:
        result = await get_client().post(f"/printers/{printer_id}/print/stop")
        return f"Print stopped on printer {printer_id}. The job has been cancelled."
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def set_chamber_light(printer_id: int, on: bool) -> str:
    """Turn the chamber light on or off for a printer.

    Args:
        printer_id: Printer ID (use list_printers to find IDs)
        on: True to turn on, False to turn off
    """
    try:
        result = await get_client().post(
            f"/printers/{printer_id}/chamber-light", params={"on": str(on).lower()}
        )
        state = "on" if on else "off"
        return f"Chamber light turned {state} on printer {printer_id}."
    except Exception as e:
        return _format_error(e)


# ============================================================
# TOOLS: Print Queue
# ============================================================


@mcp.tool()
async def list_print_queue(
    printer_id: int | None = None, status: str | None = None
) -> str:
    """List print queue items.

    Optionally filter by printer ID or status. Shows job names, positions,
    scheduled times, and current status.

    Args:
        printer_id: Filter by printer ID (optional, -1 for unassigned)
        status: Filter by status: "pending", "printing", "completed", "failed", "cancelled" (optional)
    """
    try:
        params: dict = {}
        if printer_id is not None:
            params["printer_id"] = printer_id
        if status:
            params["status"] = status
        items = await get_client().get("/queue/", params=params or None)
        if not items:
            return "Print queue is empty."

        lines = ["## Print Queue"]
        for item in items:
            name = (
                item.get("archive_name")
                or item.get("library_file_name")
                or f"Archive #{item.get('archive_id', '?')}"
            )
            st = item.get("status", "unknown")
            printer = item.get("printer_name") or (
                f"Printer #{item['printer_id']}" if item.get("printer_id") else "Unassigned"
            )
            pos = item.get("position", "?")
            est_time = _fmt_time(item.get("print_time_seconds"))
            scheduled = item.get("scheduled_time") or "ASAP"
            lines.append(
                f"- **#{item['id']}** [{st}] {name} -> {printer} "
                f"(pos: {pos}, est: {est_time}, scheduled: {scheduled})"
            )
        return "\n".join(lines)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def add_to_print_queue(
    printer_id: int | None = None,
    archive_id: int | None = None,
    library_file_id: int | None = None,
    plate_id: int | None = None,
    bed_levelling: bool = True,
    use_ams: bool = True,
) -> str:
    """Add a print job to the queue.

    Specify either archive_id (from print archives) or library_file_id
    (from file library), and optionally assign to a specific printer.

    Args:
        printer_id: Target printer ID (optional, None = unassigned)
        archive_id: Archive ID to print (use list_archives or search_archives to find)
        library_file_id: Library file ID to print (use list_library_files to find)
        plate_id: Plate number for multi-plate 3MF files (optional)
        bed_levelling: Enable bed levelling before print (default: True)
        use_ams: Use AMS for filament (default: True)
    """
    try:
        if not archive_id and not library_file_id:
            return "Error: You must specify either archive_id or library_file_id."

        body: dict = {
            "bed_levelling": bed_levelling,
            "use_ams": use_ams,
        }
        if printer_id is not None:
            body["printer_id"] = printer_id
        if archive_id is not None:
            body["archive_id"] = archive_id
        if library_file_id is not None:
            body["library_file_id"] = library_file_id
        if plate_id is not None:
            body["plate_id"] = plate_id

        result = await get_client().post("/queue/", json=body)
        item_id = result.get("id", "?")
        return f"Added to print queue (queue item #{item_id})."
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def cancel_queue_item(item_id: int) -> str:
    """Cancel a pending queue item. Only pending items can be cancelled.

    Args:
        item_id: Queue item ID (use list_print_queue to find IDs)
    """
    try:
        result = await get_client().post(f"/queue/{item_id}/cancel")
        return f"Queue item #{item_id} cancelled."
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def delete_queue_item(item_id: int) -> str:
    """Remove a queue item entirely. Cannot delete items that are currently printing.

    Args:
        item_id: Queue item ID (use list_print_queue to find IDs)
    """
    try:
        result = await get_client().delete(f"/queue/{item_id}")
        return f"Queue item #{item_id} deleted."
    except Exception as e:
        return _format_error(e)


# ============================================================
# TOOLS: Print Archives
# ============================================================


@mcp.tool()
async def list_archives(
    printer_id: int | None = None, limit: int = 20, offset: int = 0
) -> str:
    """List print archives (history of completed, failed, and in-progress prints).

    Returns print names, status, filament usage, print times, and metadata.

    Args:
        printer_id: Filter by printer ID (optional)
        limit: Maximum number of results (default: 20, max: 100)
        offset: Skip this many results for pagination (default: 0)
    """
    try:
        params: dict = {"limit": min(limit, 100), "offset": offset}
        if printer_id is not None:
            params["printer_id"] = printer_id
        archives = await get_client().get("/archives/", params=params)
        if not archives:
            return "No print archives found."

        lines = ["## Print Archives"]
        for a in archives:
            name = a.get("print_name") or a.get("filename", "Unknown")
            st = a.get("status", "unknown")
            filament = a.get("filament_type") or "N/A"
            grams = a.get("filament_used_grams")
            grams_str = f"{grams:.1f}g" if grams else "N/A"
            est_time = _fmt_time(a.get("print_time_seconds"))
            actual_time = _fmt_time(a.get("actual_time_seconds"))
            date = (a.get("created_at") or "")[:10]
            fav = " *" if a.get("is_favorite") else ""
            tags = f" [{a['tags']}]" if a.get("tags") else ""

            lines.append(
                f"- **{name}** (ID: {a['id']}) [{st}]{fav}{tags}\n"
                f"  {filament} {grams_str} | Est: {est_time} | Actual: {actual_time} | {date}"
            )
        return "\n".join(lines)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def search_archives(
    q: str,
    printer_id: int | None = None,
    status: str | None = None,
    limit: int = 20,
) -> str:
    """Search print archives by keyword.

    Searches across print names, filenames, tags, notes, designer names,
    and filament types. Supports partial matches.

    Args:
        q: Search query (minimum 2 characters)
        printer_id: Filter by printer ID (optional)
        status: Filter by status: "completed", "failed", "printing" (optional)
        limit: Maximum number of results (default: 20)
    """
    try:
        params: dict = {"q": q, "limit": min(limit, 100)}
        if printer_id is not None:
            params["printer_id"] = printer_id
        if status:
            params["status"] = status
        archives = await get_client().get("/archives/search", params=params)
        if not archives:
            return f"No archives found matching '{q}'."

        lines = [f"## Archives matching '{q}'"]
        for a in archives:
            name = a.get("print_name") or a.get("filename", "Unknown")
            st = a.get("status", "unknown")
            filament = a.get("filament_type") or "N/A"
            grams = a.get("filament_used_grams")
            grams_str = f"{grams:.1f}g" if grams else "N/A"
            date = (a.get("created_at") or "")[:10]
            lines.append(
                f"- **{name}** (ID: {a['id']}) [{st}] {filament} {grams_str} | {date}"
            )
        return "\n".join(lines)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_archive_stats() -> str:
    """Get aggregate printing statistics across all archives.

    Includes total prints, success/failure counts, total print time,
    filament usage, costs, energy consumption, and breakdowns by
    filament type and printer.
    """
    try:
        s = await get_client().get("/archives/stats")
        total = s.get("total_prints", 0)
        ok = s.get("successful_prints", 0)
        fail = s.get("failed_prints", 0)
        rate = f"{ok / total * 100:.1f}%" if total > 0 else "N/A"

        lines = [
            "## Printing Statistics",
            f"- **Total prints:** {total} (success: {ok}, failed: {fail}, rate: {rate})",
            f"- **Total print time:** {s.get('total_print_time_hours', 0):.1f} hours",
            f"- **Total filament used:** {s.get('total_filament_grams', 0):.0f}g",
            f"- **Total cost:** {s.get('total_cost', 0):.2f}",
            f"- **Total energy:** {s.get('total_energy_kwh', 0):.2f} kWh ({s.get('total_energy_cost', 0):.2f} cost)",
        ]

        accuracy = s.get("average_time_accuracy")
        if accuracy is not None:
            lines.append(f"- **Avg time accuracy:** {accuracy:.1f}%")

        by_filament = s.get("prints_by_filament_type", {})
        if by_filament:
            lines.append("\n### By Filament Type")
            for ft, count in sorted(by_filament.items(), key=lambda x: -x[1]):
                lines.append(f"- {ft}: {count} prints")

        by_printer = s.get("prints_by_printer", {})
        if by_printer:
            lines.append("\n### By Printer")
            for name, count in sorted(by_printer.items(), key=lambda x: -x[1]):
                lines.append(f"- {name}: {count} prints")

        return "\n".join(lines)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def update_archive(
    archive_id: int,
    notes: str | None = None,
    tags: str | None = None,
    is_favorite: bool | None = None,
    status: str | None = None,
) -> str:
    """Update metadata on a print archive.

    Can set notes, tags, mark as favorite, or change status.

    Args:
        archive_id: Archive ID to update
        notes: Set or update notes text (optional)
        tags: Set or update tags, comma-separated (optional)
        is_favorite: Mark or unmark as favorite (optional)
        status: Change status, e.g. "completed", "failed" (optional)
    """
    try:
        body: dict = {}
        if notes is not None:
            body["notes"] = notes
        if tags is not None:
            body["tags"] = tags
        if is_favorite is not None:
            body["is_favorite"] = is_favorite
        if status is not None:
            body["status"] = status
        if not body:
            return "Error: No fields to update. Specify at least one of: notes, tags, is_favorite, status."
        result = await get_client().patch(f"/archives/{archive_id}", json=body)
        name = result.get("print_name") or result.get("filename", f"#{archive_id}")
        return f"Archive '{name}' (ID: {archive_id}) updated."
    except Exception as e:
        return _format_error(e)


# ============================================================
# TOOLS: Filaments
# ============================================================


@mcp.tool()
async def list_filaments() -> str:
    """List all filaments in the inventory.

    Shows type, brand, color, cost per kg, and temperature settings
    for each filament.
    """
    try:
        filaments = await get_client().get("/filaments/")
        if not filaments:
            return "No filaments in inventory."

        lines = ["## Filament Inventory"]
        for f in filaments:
            name = f.get("name", "Unknown")
            ftype = f.get("type", "N/A")
            brand = f.get("brand", "")
            color = f.get("color", "")
            cost = f.get("cost_per_kg")
            cost_str = f"${cost:.2f}/kg" if cost else "N/A"
            lines.append(
                f"- **{name}** (ID: {f.get('id')}) - {brand} {ftype} {color} | {cost_str}"
            )
        return "\n".join(lines)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def add_filament(
    name: str,
    type: str,
    brand: str = "",
    color: str = "",
    cost_per_kg: float | None = None,
) -> str:
    """Add a new filament to the inventory.

    Args:
        name: Display name for the filament (e.g. "Bambu PLA Basic White")
        type: Filament type (e.g. "PLA", "PETG", "ABS", "TPU", "ASA")
        brand: Brand name (e.g. "Bambu Lab", "eSUN") (optional)
        color: Color name or hex code (optional)
        cost_per_kg: Cost per kilogram (optional)
    """
    try:
        body: dict = {"name": name, "type": type}
        if brand:
            body["brand"] = brand
        if color:
            body["color"] = color
        if cost_per_kg is not None:
            body["cost_per_kg"] = cost_per_kg
        result = await get_client().post("/filaments/", json=body)
        fid = result.get("id", "?")
        return f"Filament '{name}' added (ID: {fid})."
    except Exception as e:
        return _format_error(e)


# ============================================================
# TOOLS: Maintenance
# ============================================================


@mcp.tool()
async def get_maintenance_overview() -> str:
    """Get maintenance status overview for all active printers.

    Shows which maintenance tasks are due, upcoming, or overdue,
    with hours tracking for each task.
    """
    try:
        overview = await get_client().get("/maintenance/overview")
        if not overview:
            return "No maintenance data available."

        lines = ["## Maintenance Overview"]
        for printer in overview:
            name = printer.get("printer_name", f"Printer #{printer.get('printer_id')}")
            total_hours = printer.get("total_print_hours", 0)
            lines.append(f"\n### {name} ({total_hours:.0f} total print hours)")

            items = printer.get("items", [])
            if not items:
                lines.append("  No maintenance items configured.")
                continue

            for item in items:
                mtype = item.get("type_name", "Unknown")
                hours_since = item.get("hours_since_last", 0)
                interval = item.get("interval_hours", 0)
                is_due = item.get("is_due", False)
                is_warning = item.get("is_warning", False)
                flag = " **[DUE]**" if is_due else (" [soon]" if is_warning else "")
                lines.append(
                    f"  - {mtype}: {hours_since:.0f}h since last (interval: {interval}h){flag}"
                )
        return "\n".join(lines)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_printer_maintenance(printer_id: int) -> str:
    """Get detailed maintenance status for a specific printer.

    Shows all maintenance tasks with intervals, time since last performed,
    and due status.

    Args:
        printer_id: Printer ID (use list_printers to find IDs)
    """
    try:
        data = await get_client().get(f"/maintenance/printers/{printer_id}")
        name = data.get("printer_name", f"Printer #{printer_id}")
        total_hours = data.get("total_print_hours", 0)
        lines = [f"## Maintenance: {name} ({total_hours:.0f} total hours)"]

        items = data.get("items", [])
        if not items:
            lines.append("No maintenance items configured.")
            return "\n".join(lines)

        for item in items:
            mtype = item.get("type_name", "Unknown")
            hours_since = item.get("hours_since_last", 0)
            interval = item.get("interval_hours", 0)
            is_due = item.get("is_due", False)
            is_warning = item.get("is_warning", False)
            last_performed = item.get("last_performed_at", "Never")
            flag = " **[DUE]**" if is_due else (" [soon]" if is_warning else " OK")
            lines.append(
                f"- **{mtype}**{flag}\n"
                f"  {hours_since:.0f}h since last | interval: {interval}h | last: {last_performed}"
            )
        return "\n".join(lines)
    except Exception as e:
        return _format_error(e)


# ============================================================
# TOOLS: Library & Files
# ============================================================


@mcp.tool()
async def list_library_files(
    folder_id: int | None = None, limit: int = 50, offset: int = 0
) -> str:
    """List files in the print library (uploaded 3MF/gcode files).

    These files can be added to the print queue using add_to_print_queue.

    Args:
        folder_id: Filter by folder ID (optional)
        limit: Maximum number of results (default: 50)
        offset: Skip this many results for pagination (default: 0)
    """
    try:
        params: dict = {"limit": min(limit, 100), "offset": offset}
        if folder_id is not None:
            params["folder_id"] = folder_id
        files = await get_client().get("/library/files", params=params)
        if not files:
            return "No files in the library."

        lines = ["## Library Files"]
        for f in files:
            name = f.get("filename", "Unknown")
            fid = f.get("id", "?")
            meta = f.get("file_metadata", {}) or {}
            filament = meta.get("filament_type", "")
            est_time = _fmt_time(meta.get("print_time_seconds"))
            lines.append(f"- **{name}** (ID: {fid}) {filament} | Est: {est_time}")
        return "\n".join(lines)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def list_printer_files(printer_id: int, path: str = "/") -> str:
    """List files stored on a printer's internal storage or SD card.

    Browse the file system by specifying a path.

    Args:
        printer_id: Printer ID (use list_printers to find IDs)
        path: Directory path to list (default: root "/")
    """
    try:
        params = {"path": path}
        files = await get_client().get(f"/printers/{printer_id}/files", params=params)
        if not files:
            return f"No files found at '{path}' on printer {printer_id}."

        lines = [f"## Files on Printer #{printer_id} ({path})"]
        for f in files:
            if isinstance(f, dict):
                name = f.get("name", "Unknown")
                ftype = "DIR" if f.get("is_directory") else "FILE"
                size = f.get("size", 0)
                size_str = f" ({size / 1024:.1f} KB)" if size and not f.get("is_directory") else ""
                lines.append(f"- [{ftype}] {name}{size_str}")
            else:
                lines.append(f"- {f}")
        return "\n".join(lines)
    except Exception as e:
        return _format_error(e)


# ============================================================
# TOOLS: Settings
# ============================================================


@mcp.tool()
async def get_settings() -> str:
    """Get all Bambuddy application settings.

    Returns configuration including auto-archive preferences, notification
    settings, spoolman integration, energy costs, and more.
    """
    try:
        settings = await get_client().get("/settings/")
        return f"## Bambuddy Settings\n```json\n{json.dumps(settings, indent=2, ensure_ascii=False)}\n```"
    except Exception as e:
        return _format_error(e)


# ============================================================
# RESOURCES
# ============================================================


@mcp.resource("bambuddy://printers")
async def resource_printers() -> str:
    """List of all configured printers with names, models, and IDs."""
    return await list_printers()


@mcp.resource("bambuddy://printers/{printer_id}/status")
async def resource_printer_status(printer_id: int) -> str:
    """Real-time status of a specific printer."""
    return await get_printer_status(printer_id)


@mcp.resource("bambuddy://stats")
async def resource_stats() -> str:
    """Aggregate printing statistics."""
    return await get_archive_stats()


@mcp.resource("bambuddy://system")
async def resource_system() -> str:
    """System information and health."""
    return await get_system_info()


# ============================================================
# Entry Point
# ============================================================


def main():
    """Run the Bambuddy MCP server with stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
