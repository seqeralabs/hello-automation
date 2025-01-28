# @@@SNIPSTART python-money-transfer-project-template-shared
from dataclasses import dataclass

SEQUENCER_TASK_QUEUE_NAME = "SEQUENCER_TASK_QUEUE"
SEQERA_TASK_QUEUE_NAME = "SEQERA_TASK_QUEUE"


@dataclass
class SequencingRun:
    run_id: str
    reference_id: str


# @@@SNIPEND