"""Semantic design tokens for the current dark Velora theme."""
from enum import Enum


class Colors:
    BACKGROUND_PRIMARY = "#05090D"
    BACKGROUND_SECONDARY = "#071016"
    BACKGROUND_ELEVATED = "#0B141C"
    BACKGROUND_HOVER = "#181022"
    BACKGROUND_SELECTED = "#1B1028"
    SURFACE_CARD = "#0E161F"
    SURFACE_CARD_HOVER = "#151020"
    SURFACE_INPUT = "#091118"
    SURFACE_DISABLED = "#080D12"
    BORDER_DEFAULT = "#293642"
    BORDER_SUBTLE = "#23303B"
    BORDER_HOVER = "#8241C9"
    BORDER_ACTIVE = "#A33CFF"
    TEXT_PRIMARY = "#EEF1F4"
    TEXT_SECONDARY = "#B6C0CA"
    TEXT_MUTED = "#8995A1"
    TEXT_DISABLED = "#56616C"
    TEXT_ON_ACCENT = "#F6F0FC"
    ACCENT_PRIMARY = "#A33CFF"
    ACCENT_HOVER = "#B653FF"
    ACCENT_PRESSED = "#7A22C8"
    ACCENT_SUBTLE = "#1B1028"
    ACCENT_GLOW = "#552080"
    STATUS_COMPLETED = "#20C875"
    STATUS_CURRENT = ACCENT_PRIMARY
    STATUS_IN_PROGRESS = "#E88932"
    STATUS_NOT_STARTED = "#66717D"
    STATUS_ABANDONED = "#E04B4B"
    RATING_HIGH = "#20C875"
    RATING_MEDIUM = "#F7C431"
    RATING_LOW = "#E04B4B"
    MOOD_EXCITED = "#35D07F"
    MOOD_HAPPY = "#57C97B"
    MOOD_POSITIVE = "#84C96A"
    MOOD_NEUTRAL = "#8B96A1"
    MOOD_TIRED = "#B59B5A"
    MOOD_BORED = "#8B7C73"
    MOOD_DISAPPOINTED = "#D36B55"
    MOOD_ANGRY = "#E04B4B"
    DANGER = "#E04B4B"
    WARNING = "#F7C431"
    SUCCESS = "#20C875"
    INFO = "#4E9BF5"


class Spacing:
    SPACE_2 = 2
    SPACE_4 = 4
    SPACE_6 = 6
    SPACE_8 = 8
    SPACE_12 = 12
    SPACE_16 = 16
    SPACE_20 = 20
    SPACE_24 = 24
    SPACE_32 = 32
    SPACE_40 = 40


class Radii:
    SMALL = 4
    MEDIUM = 6
    LARGE = 9
    CARD = 9
    PILL = 999


class Dimensions:
    BUTTON_HEIGHT = 36
    BUTTON_COMPACT_HEIGHT = 30
    FIELD_HEIGHT = 36
    ICON_SMALL = 16
    ICON_MEDIUM = 20
    ICON_LARGE = 24
    JOURNEY_STAGE_CARD_WIDTH = 190
    JOURNEY_STAGE_CARD_HEIGHT = 160
    # The selector must fit "ПРОХОЖДЕНИЕ №NN" together with its action button
    # without eliding the historical sequence number.
    JOURNEY_SUMMARY_WIDTH = 280
    # Journey 3.1 geometry: these bounds describe the three page zones, not
    # one target resolution.  Their ranges allow the layout to fit 1366 px
    # wide workspaces while using the additional vertical room at Full HD/2K.
    JOURNEY_ROUTE_MIN_HEIGHT = 330
    JOURNEY_ROUTE_BASELINE_HEIGHT = 350
    JOURNEY_ROUTE_MAX_HEIGHT = 520
    JOURNEY_DETAIL_MIN_HEIGHT = 205
    JOURNEY_DETAIL_BASELINE_HEIGHT = 215
    JOURNEY_DETAIL_MAX_HEIGHT = 275
    JOURNEY_ANALYTICS_MIN_HEIGHT = 118
    JOURNEY_ANALYTICS_BASELINE_HEIGHT = 128
    JOURNEY_ANALYTICS_MAX_HEIGHT = 195
    JOURNEY_EVENT_AREA_HEIGHT = 184
    JOURNEY_IMAGE_WIDTH = 330
    JOURNEY_ACTION_CARD_WIDTH = 110
    JOURNEY_ACTION_CARD_HEIGHT = 76
    JOURNEY_SCROLL_ARROW_WIDTH = 38
    JOURNEY_SCROLL_ARROW_HEIGHT = 48
    JOURNEY_COMPACT_ROUTE_HEIGHT = JOURNEY_ROUTE_BASELINE_HEIGHT
    JOURNEY_COMPACT_DETAIL_HEIGHT = JOURNEY_DETAIL_BASELINE_HEIGHT
    JOURNEY_COMPACT_ANALYTICS_HEIGHT = JOURNEY_ANALYTICS_BASELINE_HEIGHT
    JOURNEY_COMPACT_EDITOR_PREVIEW_HEIGHT = 82
    JOURNEY_COMPACT_STAGE_WIDTH = JOURNEY_STAGE_CARD_WIDTH
    JOURNEY_COMPACT_STAGE_HEIGHT = JOURNEY_STAGE_CARD_HEIGHT
    JOURNEY_COMPACT_EVENT_HEIGHT = JOURNEY_EVENT_AREA_HEIGHT
    JOURNEY_COMPACT_IMAGE_WIDTH = 310
    # Compatibility aliases for components introduced in the first pass.
    STAGE_CARD_MIN_WIDTH = JOURNEY_STAGE_CARD_WIDTH
    STAGE_CARD_HEIGHT = JOURNEY_STAGE_CARD_HEIGHT
    JOURNEY_SIDEBAR_WIDTH = JOURNEY_SUMMARY_WIDTH
    ACTIVE_BORDER = 1
    JOURNEY_LINE = 2
    SCROLLBAR_HEIGHT = 8


class Motion:
    FAST = 120
    NORMAL = 180
    EMPHASIS = 220
    FAVORITE_DURATION = 420
    FAVORITE_ADD_SCALE = 1.70
    FAVORITE_REMOVE_SCALE = 1.50


class Typography:
    DISPLAY = "font-size:26pt;font-weight:800;"
    PAGE_TITLE = "font-size:20pt;font-weight:750;"
    SECTION_TITLE = "font-size:12pt;font-weight:800;"
    CARD_TITLE = "font-size:10pt;font-weight:700;"
    BODY = "font-size:10pt;font-weight:400;"
    BODY_SECONDARY = "font-size:9pt;font-weight:400;"
    LABEL = "font-size:9pt;font-weight:600;"
    CAPTION = "font-size:8pt;font-weight:600;"
    METRIC_LARGE = "font-size:26pt;font-weight:900;"
    METRIC_MEDIUM = "font-size:14pt;font-weight:700;"
    JOURNEY_STAGE_NUMBER = "font-size:12pt;font-weight:750;"
    JOURNEY_STAGE_TITLE = "font-size:11pt;font-weight:650;"
    JOURNEY_STAGE_STATUS = "font-size:9.5pt;font-weight:600;"
    JOURNEY_STAGE_META = "font-size:9.5pt;font-weight:450;"
    BUTTON_TEXT = "font-size:9pt;font-weight:650;"


class VisualState(str, Enum):
    DEFAULT = "default"
    HOVER = "hover"
    PRESSED = "pressed"
    SELECTED = "selected"
    FOCUSED = "focused"
    DISABLED = "disabled"
    ERROR = "error"
