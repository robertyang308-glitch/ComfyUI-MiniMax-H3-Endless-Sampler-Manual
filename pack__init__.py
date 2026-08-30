from .nodes import HREndlessSampler, HREndlessSamplerAdvanced
from .preview import HREndlessSamplerPreview
from .video_io import HREndlessSamplerLoadVideo, HREndlessSamplerSaveVideo

__version__ = "0.9.0"


NODE_CLASS_MAPPINGS = {
    "HREndlessSampler": HREndlessSampler,
    "HREndlessSamplerAdvanced": HREndlessSamplerAdvanced,
    "HREndlessSamplerPreview": HREndlessSamplerPreview,
    "HREndlessSamplerSaveVideo": HREndlessSamplerSaveVideo,
    "HREndlessSamplerLoadVideo": HREndlessSamplerLoadVideo,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "HREndlessSampler": "Endless Sampler",
    "HREndlessSamplerAdvanced": "Endless Sampler (Advanced)",
    "HREndlessSamplerPreview": "Endless Sampler Preview",
    "HREndlessSamplerSaveVideo": "Endless Sampler Save Video",
    "HREndlessSamplerLoadVideo": "Endless Sampler Load Video",
}

WEB_DIRECTORY = "./web"

__all__ = ["__version__", "NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
