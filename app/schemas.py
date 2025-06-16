# app/api/schemas.py
from pydantic import BaseModel, Field, EmailStr
from typing import Dict, Any, Optional, List

# --- Modelos Genéricos ---
class ErrorResponse(BaseModel):
    detail: Any

# --- Modelos Específicos de Correo ---
class EmailAddress(BaseModel):
    address: EmailStr
    name: Optional[str] = None

class Recipient(BaseModel):
    emailAddress: EmailAddress

class EmailBody(BaseModel):
    contentType: str = "HTML"
    content: str

class Attachment(BaseModel):
    odata_type: str = Field(alias="@odata.type", default="#microsoft.graph.fileAttachment")
    name: str
    contentBytes: str # Base64 encoded content

class EmailMessage(BaseModel):
    id: Optional[str] = None
    subject: Optional[str] = None
    bodyPreview: Optional[str] = None
    body: Optional[EmailBody] = None
    toRecipients: Optional[List[Recipient]] = []
    ccRecipients: Optional[List[Recipient]] = []
    from_prop: Optional[Recipient] = Field(None, alias="from")
    sender: Optional[Recipient] = None
    receivedDateTime: Optional[str] = None
    webLink: Optional[str] = None
    
    class Config:
        populate_by_name = True

class SendMessagePayload(BaseModel):
    to_recipients: List[Recipient]
    subject: str
    body_content: str
    body_type: str = "HTML"
    cc_recipients: Optional[List[Recipient]] = None
    bcc_recipients: Optional[List[Recipient]] = None
    attachments: Optional[List[Attachment]] = None
    save_to_sent_items: bool = True

class ReplyMessagePayload(BaseModel):
    comment: str
    reply_all: bool = False

class ForwardMessagePayload(BaseModel):
    to_recipients: List[Recipient]
    comment: Optional[str] = None

class MoveMessagePayload(BaseModel):
    destination_folder_id: str

class MailFolder(BaseModel):
    id: Optional[str] = None
    displayName: Optional[str] = None
    parentFolderId: Optional[str] = None
    childFolderCount: Optional[int] = None
    unreadItemCount: Optional[int] = None
    totalItemCount: Optional[int] = None

class CreateFolderPayload(BaseModel):
    folder_name: str

# --- Modelos Específicos de Calendario ---
class DateTimeTimeZone(BaseModel):
    dateTime: str
    timeZone: str = "UTC"

class Location(BaseModel):
    displayName: str
    locationType: Optional[str] = None
    uniqueId: Optional[str] = None
    uniqueIdType: Optional[str] = None

class Event(BaseModel):
    id: Optional[str] = None
    subject: Optional[str] = None
    bodyPreview: Optional[str] = None
    body: Optional[EmailBody] = None
    start: Optional[DateTimeTimeZone] = None
    end: Optional[DateTimeTimeZone] = None
    location: Optional[Location] = None
    locations: Optional[List[Location]] = []
    attendees: Optional[List[Recipient]] = []
    organizer: Optional[Recipient] = None
    webLink: Optional[str] = None

class CreateEventPayload(BaseModel):
    subject: str
    body: EmailBody
    start: DateTimeTimeZone
    end: DateTimeTimeZone
    attendees: Optional[List[Recipient]] = None
    location: Optional[Location] = None

class UpdateEventPayload(BaseModel):
    subject: Optional[str] = None
    body: Optional[EmailBody] = None
    start: Optional[DateTimeTimeZone] = None
    end: Optional[DateTimeTimeZone] = None
    attendees: Optional[List[Recipient]] = None
    location: Optional[Location] = None

class TimeConstraint(BaseModel):
    start: DateTimeTimeZone
    end: DateTimeTimeZone

class FindMeetingTimesPayload(BaseModel):
    attendees: List[Recipient]
    timeConstraint: TimeConstraint
    meetingDuration: str = "PT30M" # Formato ISO 8601 de duración
    maxCandidates: int = 15

class MeetingTimeSuggestion(BaseModel):
    meetingTimeSlot: Optional[dict] = None # El objeto TimeSlot es complejo, lo dejamos como dict
    confidence: Optional[float] = None
    organizerAvailability: Optional[str] = None
    attendeeAvailability: Optional[List[dict]] = []

class MeetingTimeSuggestionResult(BaseModel):
    meetingTimeSuggestions: Optional[List[MeetingTimeSuggestion]] = []
    emptySuggestionsReason: Optional[str] = None

class GetSchedulePayload(BaseModel):
    schedules: List[str] # Lista de correos de los usuarios
    startTime: DateTimeTimeZone
    endTime: DateTimeTimeZone
    availabilityViewInterval: int = 30

class ScheduleInformation(BaseModel):
    scheduleId: Optional[str] = None
    availabilityView: Optional[str] = None
    scheduleItems: Optional[List[dict]] = []