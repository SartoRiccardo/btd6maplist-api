from dataclasses import dataclass
from ..data_utils import dateify, SEPARATOR, stringify


@dataclass
class MapSubmission:
    id: int
    code: str
    submitter: int
    subm_notes: str | None
    for_list: int
    proposed: int
    rejected_by: int | None
    created_on: int
    completion_proof: str
    wh_data: str | None
    wh_msg_id: int | None

    def dump_submission(self) -> str:
        return SEPARATOR.join(stringify(
            self.code,
            self.submitter,
            self.subm_notes,
            self.for_list,
            self.proposed,
            self.rejected_by,
            dateify(self.created_on),
            self.completion_proof,
            self.wh_data,
            self.wh_msg_id,
            self.id,
        ))
