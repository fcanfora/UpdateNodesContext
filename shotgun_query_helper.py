import re
import sgtk
import os

PUBLISH_STATUSES = ["ta", "apr"]

class ShotGunQuery:
    def __init__(self, loader_name="tk-multi-loader2"):
        self.loader_name = loader_name
        self.engine = None
        self.loader_app = None
        self.project = None
        self.shot = None

    def set_shotgun(self, shot_context=True):
        """Initialize Toolkit engine, project and shot context"""
        self.engine = sgtk.platform.current_engine()
        self.project = self.engine.context.project['name']
        if shot_context:
            self.shot = self.engine.context.entity
            self.loader_app = self.engine.apps.get(self.loader_name)

    def build_path_from_template(self, template_path, **custom_fields):
        """
        Build a new path from a file-system template path and field overrides.
        Returns the first matching filesystem path.
        """
        # Infer Toolkit instance from the path
        tk = sgtk.sgtk_from_path(template_path)
        templates = tk.templates_from_path(template_path)
        if not templates:
            return None
        template = templates[0]
        fields = template.get_fields(template_path)
        fields.update(custom_fields)
        paths = tk.paths_from_template(template, fields)
        return paths[0] if paths else None

    def build_path_from_template_name(self, template_name, fields):
        """
        Build a new path given an SG template name and a dictionary of fields.
        Useful for templates like 'houdini_shot_publish_filecache'.
        """
        if not self.engine:
            raise RuntimeError("Shotgun engine not initialized. Call set_shotgun() first.")
        tk = self.engine.sgtk
        template = tk.templates.get(template_name)
        if not template:
            return None
        return template.apply_fields(fields)

    def query_latest(self, filters, order):
        """
        Query ShotGrid for the latest PublishedFile matching filters and order.
        """
        sg = self.engine.shotgun
        return sg.find_one(
            "PublishedFile",
            filters,
            ["path", "version_number"],
            order=order
        )
