from __future__ import annotations

from knowledge_engine.profiles.assets import HtmlAssetsProfile
from knowledge_engine.profiles.base import OutputProfile, ProfileOutput
from knowledge_engine.profiles.clean import CleanHtmlProfile
from knowledge_engine.profiles.freshservice import FreshserviceProfile


PROFILES: dict[str, OutputProfile] = {
    profile.id: profile for profile in (CleanHtmlProfile(), HtmlAssetsProfile(), FreshserviceProfile())
}

__all__ = ["PROFILES", "OutputProfile", "ProfileOutput"]
