from sqlmodel import Session, SQLModel, create_engine
from src.api.database import Job, JobStatus

test_engine = create_engine("sqlite:///:memory:", echo=False)
SQLModel.metadata.create_all(test_engine)

# Insert Job
with Session(test_engine) as session:
    test_job = Job(job_id="test_101", user_id="usr_demo", status=JobStatus.PLANNING)
    session.add(test_job)
    session.commit()

# Query back in a completely fresh session
with Session(test_engine) as session:
    retrieved_job = session.get(Job, "test_101")
    
    print(f"Retrieved status: {retrieved_job.status!r}")
    print(f"Is instance of JobStatus? -> {isinstance(retrieved_job.status, JobStatus)}")
    
    assert isinstance(retrieved_job.status, JobStatus), "Failed: status returned as raw str!"
    assert retrieved_job.status == JobStatus.PLANNING, "Failed: status value mismatch!"
    print("Smoke Test Passed Successfully!")