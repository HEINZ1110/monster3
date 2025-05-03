class ImageMetadata:
    """Stores metadata associated with an image."""

    def __init__(self, filename: str, physical_size: str = "", category: str = "", text: str = "", comment: str = "", condition: str = "", date: str = "", location: str = "", artist: str = "", provenance: str = "", custom_metadata: dict = None):
        self.filename = filename
        self.physical_size = physical_size
        self.category = category
        self.text = text
        self.comment = comment
        self.condition = condition
        self.date = date
        self.location = location
        self.artist = artist
        self.provenance = provenance
        self.custom_metadata = custom_metadata if custom_metadata is not None else {}

    def to_dict(self) -> dict:
        """Converts metadata to a dictionary."""
        return {
            "filename": self.filename,
            "physical_size": self.physical_size,
            "category": self.category,
            "text": self.text,
            "comment": self.comment,
            "condition": self.condition,
            "date": self.date,
            "location": self.location,
            "artist": self.artist,
            "provenance": self.provenance,
            "custom_metadata": self.custom_metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ImageMetadata":
        """Creates metadata from a dictionary."""
        return cls(
            filename=data.get("filename", ""),
            physical_size=data.get("physical_size", ""),
            category=data.get("category", ""),
            text=data.get("text", ""),
            comment=data.get("comment", ""),
            condition=data.get("condition", ""),
            date=data.get("date", ""),
            location=data.get("location", ""),
            artist=data.get("artist", ""),
            provenance=data.get("provenance", ""),
            custom_metadata=data.get("custom_metadata", {})
        )