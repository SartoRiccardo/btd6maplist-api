from dataclasses import dataclass
from datetime import datetime
from src.utils.misc import list_to_int


@dataclass
class MapSubmission:
    """
    type: object
    properties:
      code:
        type: string
        description: The code of the submitted map.
      submitter:
        $ref: "#/components/schemas/DiscordID"
      subm_notes:
        type: string
        nullable: true
        description: Additional notes provided in the submission.
      type:
        type: string
        enum: ["experts", "list"]
        description: The list the submission is for.
      proposed_difficulty:
        type: string
        description: The proposed difficulty
      rejected_by:
        $ref: "#/components/schemas/DiscordID"
        nullable: true
      created_on:
        type: int
        description: Date of the submission.
    """
    code: str
    submitter: int
    subm_notes: str | None
    for_list: int
    proposed_diff: int
    rejected_by: int | None
    created_on: datetime
    wh_data: str | None

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "submitter": self.submitter,
            "subm_notes": self.subm_notes,
            "type": list_to_int[self.for_list],
            "proposed_diff": self.proposed_diff,
            "rejected_by": self.rejected_by,
            "created_on": int(self.created_on.timestamp()),
        }
