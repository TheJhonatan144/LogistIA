from app.core.database import save_log


def log_info(event: str, detail: str) -> None:
    save_log(event=event, detail=detail)


def log_error(event: str, detail: str) -> None:
    save_log(event=event, detail=f"[ERROR] {detail}")
    