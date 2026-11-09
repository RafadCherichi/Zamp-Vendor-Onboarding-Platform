"""Local query/latency diagnostic; not a hosted-service performance claim."""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix="zamp-queue-benchmark-") as directory:
    os.environ.update(DATABASE_URL=f"sqlite:///{Path(directory).as_posix()}/queue.db", GEMINI_API_KEY="")
    sys.path.insert(0, str(ROOT / "backend"))
    from sqlalchemy import event
    from app.database import Base, engine, SessionLocal
    import app.models
    from app.models.organization import Organization
    from app.models.vendor import Vendor
    from app.models.application import Application
    from app.models.validation import ValidationRun
    from app.services.review.queue_service import QueueAndDashboardService
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        org = Organization(name="Synthetic queue benchmark", slug="benchmark")
        db.add(org)
        db.flush()
        vendor = Vendor(organisation_id=org.id, legal_name="Benchmark supplier", constitution="PROPRIETORSHIP")
        db.add(vendor)
        db.commit()
        org_id, vendor_id = org.id, vendor.id
    count = [0]
    def count_query(*args):
        count[0] += 1
    event.listen(engine, "before_cursor_execute", count_query)
    results = []
    previous = 0
    for size in [10, 100, 500]:
        with SessionLocal() as db:
            for index in range(previous, size):
                case = Application(organisation_id=org_id, vendor_id=vendor_id, reference_number=f"BENCH-{index}", legal_name=f"Synthetic supplier {index}", status="UNDER_REVIEW")
                db.add(case)
                db.flush()
                db.add(ValidationRun(application_id=case.id, organisation_id=org_id, status="COMPLETED", is_current=True))
            db.commit()
        previous = size
        for ready in [False, True]:
            with SessionLocal() as db:
                count[0] = 0
                start = time.perf_counter()
                response = QueueAndDashboardService(db).query_queue(org_id, ready_for_approval_only=ready, page_size=10)
                results.append({"cases":size,"filter":"ready" if ready else "all","page_size":10,"sql_queries":count[0],"milliseconds":round((time.perf_counter()-start)*1000,1),"returned":len(response["items"])})
    event.remove(engine, "before_cursor_execute", count_query)
    engine.dispose()
    output = {"environment":"Local SQLite, minimal synthetic cases with empty document collections; one measurement per condition, not a production SLA", "results":results}
    (ROOT / "testdata/queue_benchmark.json").write_text(json.dumps(output,indent=2),encoding="utf-8")
    print(json.dumps(output))
