from dataclasses import dataclass
from datetime import datetime


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
      format:
        $ref: "#/components/schemas/MaplistFormat"
      proposed_difficulty:
        type: string
        description: The proposed difficulty
      rejected_by:
        $ref: "#/components/schemas/DiscordID"
        nullable: true
      completion_proof:
        type: string
        description: The URL to an image of the map being completed
      created_on:
        type: integer
        description: Date of the submission.
    """
    code: str
    submitter: int
    subm_notes: str | None
    format_id: int
    proposed_diff: int
    rejected_by: int | None
    created_on: datetime
    completion_proof: str
    wh_data: str | None

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "submitter": str(self.submitter),
            "subm_notes": self.subm_notes,
            "format": self.format_id,
            "proposed_diff": self.proposed_diff,
            "rejected_by": str(self.rejected_by) if self.rejected_by else None,
            "completion_proof": self.completion_proof,
            "created_on": int(self.created_on.timestamp()),
        }
