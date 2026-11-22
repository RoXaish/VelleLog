from enum import Enum


class Mood(str, Enum):
    """Supported journal entry moods."""

    HAPPY = "happy"
    CALM = "calm"
    EXCITED = "excited"
    GRATEFUL = "grateful"
    NEUTRAL = "neutral"
    SAD = "sad"
    ANXIOUS = "anxious"
    STRESSED = "stressed"


MOOD_VALUES: tuple[str, ...] = tuple(mood.value for mood in Mood)
MOOD_SQL_LIST = ", ".join(f"'{value}'" for value in MOOD_VALUES)
