from datetime import time, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class DeviceRegisterRequest(BaseModel):
    fcm_token: str = Field(min_length=1, max_length=4096, pattern=r"^\S+$")
    platform: Literal["web", "android", "ios"] = "web"

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    body: str
    is_read: bool
    created_at: datetime
    data_payload: dict = Field(default_factory=dict)


class ChannelPreference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    push: bool = True
    in_app: bool = True


class NotificationPreferencesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    per_type: dict[Literal[
        "class_reminder", "lab_reminder", "exam_reminder", "announcement",
        "course_assignment", "course_enrollment",
    ], ChannelPreference] = Field(default_factory=dict)
    quiet_start: time | None = None
    quiet_end: time | None = None

    @model_validator(mode="after")
    def quiet_pair(self):
        if (self.quiet_start is None) != (self.quiet_end is None):
            raise ValueError("Set both quiet_start and quiet_end, or neither.")
        if any(t is not None and t.tzinfo is not None for t in (self.quiet_start, self.quiet_end)):
            raise ValueError("Quiet hours are local Asia/Dhaka wall-clock times.")
        return self


class NotificationPreferencesResponse(NotificationPreferencesRequest):
    timezone: Literal["Asia/Dhaka"] = "Asia/Dhaka"
