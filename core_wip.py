#!/usr/bin/env python
# change_shot_name.py
"""
Given an existing file path under ShotGrid Toolkit control,
find its Toolkit template, extract the fields, swap in a new shot name
(or use the current shot from context if none is provided),
then update to the latest publish based on the version_filter:
- "all": latest file on disk (any status)
- "apr": latest approved only
- "ta": latest temp-approved only
- "apr_ta": latest approved or temp-approved (default)
and return the resolved path.
"""

import sys
import os
import glob
import sgtk
import hou

# ─────────────────────────────────────────────────────────────────────────────
# Configure here: node type name → list of parm names holding paths
NODE_PATH_PARMS = {
    "alembic":            ["fileName"],
    "file":               ["file"],
    "arnold::procedural": ["dso"],
    # add more node_type: [parm1, parm2] as needed
}
# ─────────────────────────────────────────────────────────────────────────────

def change_shot_in_path(
    original_path,
    new_shot_name=None,
    version_filter="apr_ta"
):
    """
    Swap the shot token in a path, then update to latest publish
    based on version_filter and return the resolved path.

    original_path   (str): full existing file path
    new_shot_name   (str): shot code to swap in; if None, uses context.entity.name
    version_filter  (str): one of "all", "apr", "ta", or "apr_ta"
    """
    print(f"[1] Original path: {original_path}")
    engine = sgtk.platform.current_engine()
    sg = engine.shotgun
    ctx = engine.context

    # Determine new shot name
    if not new_shot_name:
        if ctx.entity and ctx.entity.get("name"):
            new_shot_name = ctx.entity["name"]
            print(f"[1a] No shot specified — using context shot: {new_shot_name}")
        else:
            print("[ERROR] No shot provided and no Shot context available.")
            return None

    # Step 1: resolve toolkit template and extract fields
    try:
        tk = sgtk.sgtk_from_path(original_path)
        template = tk.templates_from_path(original_path)[0]
        fields = template.get_fields(original_path)
    except Exception as e:
        print(f"[ERROR] Toolkit/template resolution failed: {e}")
        return None
    print(f"[2] Using template: {template.name}")
    print("[3] Original fields:")
    for k, v in sorted(fields.items()): print(f"   {k}: {v}")

    # Swap shot
    shot_key = next((k for k in fields if k.lower() == "shot"), None) or "shot"
    fields[shot_key] = new_shot_name
    print(f"[4] Set '{shot_key}' → '{new_shot_name}'")

    # Identify version field
    version_key = next((k for k in fields if k.lower() == "version"), None)
    if not version_key:
        print("[WARNING] No version field in template — cannot update version.")
        result = template.apply_fields(fields)
        print(f"[5] New path: {result}")
        return result

    # Step 2: find original SG publish record by matching fields
    name_key = next((k for k in fields if k.lower() == "name"), None)
    if not name_key:
        print("[ERROR] No 'name' field in template — cannot query SG.")
        return None
    orig_filters = [
        ["project", "is", ctx.project],
        ["entity", "is", ctx.entity],
        ["name", "is", fields[name_key]]#,
        #["version_number", "is", fields[version_key]]
    ]
    # include file type in original lookup
    orig_pub = sg.find_one(
        "PublishedFile",
        orig_filters,
        ["id","entity","name","version_number","sg_status_list","published_file_type.PublishedFileType.code"]
    )
    if not orig_pub:
        print(f"[ERROR] Could not find original SG publish with filters: {orig_filters}")
        return None
    print(f"[5] Found original SG publish id={orig_pub['id']}, v{orig_pub['version_number']}")

    # Branch by version_filter
    if version_filter == "all":
        # list all versions on disk
        del fields[version_key]
        print("[6] Listing all versions on disk for latest (any status)")
        abstract_paths = tk.abstract_paths_from_template(template, fields)
        real_paths = []
        for p in abstract_paths:
            if "%04d" in p:
                real_paths.extend(glob.glob(p.replace("%04d","*")))
            elif os.path.exists(p):
                real_paths.append(p)
        if not real_paths:
            print("[ERROR] No files found on disk for 'all' filter.")
            return None
        real_paths.sort()
        latest = real_paths[-1]
        print(f"[7] Latest on disk: {latest}")
        return latest
    else:
        # query SG for all versions by status
        status_filter = None
        if version_filter in ("apr","ta"):
            status_filter = ["sg_status_list","is",version_filter]
        elif version_filter == "apr_ta":
            status_filter = ["sg_status_list","in",["apr","ta"]]

        ver_filters = [
            ["project","is",ctx.project],
            ["entity","is",orig_pub["entity"]],
            ["name","is",orig_pub["name"]],
            ["published_file_type.PublishedFileType.code","is",orig_pub["published_file_type.PublishedFileType.code"]]
        ]
        if status_filter:
            ver_filters.append(status_filter)
        print(f"[6] Version filters: {ver_filters}")
        results = sg.find(
            "PublishedFile", ver_filters,
            ["version_number"],
            [{"field_name":"version_number","direction":"asc"}]
        )
        ver_list = [r["version_number"] for r in results]
        if not ver_list:
            print(f"[WARNING] No SG publishes found for filter '{version_filter}' — using original v{orig_pub['version_number']}")
            latest_v = orig_pub["version_number"]
        else:
            latest_v = ver_list[-1]
        print(f"[7] SG versions: {ver_list} → latest {latest_v}")
        fields[version_key] = latest_v
        try:
            new_path = template.apply_fields(fields)
            print(f"[8] New path: {new_path}")
            return new_path
        except Exception as e:
            print(f"[ERROR] Rebuild path failed: {e}")
            return None


def update_all_node_paths(version_filter="apr_ta"):
    """
    Scan Houdini scene and update path parms for nodes in NODE_PATH_PARMS.
    version_filter passed to change_shot_in_path.
    """
    print(f">>> Updating node paths (filter='{version_filter}')...")
    for node in hou.node("/").allSubChildren():
        for parm_name in NODE_PATH_PARMS.get(node.type().name(), []):
            parm = node.parm(parm_name)
            if parm:
                orig = parm.evalAsString()
                if orig:
                    print(f"-- {node.path()}:{parm_name} = {orig}")
                    newp = change_shot_in_path(orig, None, version_filter)
                    if newp and newp != orig:
                        parm.set(newp)
                        print(f"   → {newp}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--update-nodes":
        vf = args[1] if len(args)>1 else "apr_ta"
        update_all_node_paths(vf)
        sys.exit(0)
    if not args:
        print("Usage: change_shot_name.py <path> [new_shot] [all|apr|ta|apr_ta]")
        sys.exit(1)
    orig = args[0]
    shot = args[1] if len(args)>1 and args[1] not in ("all","apr","ta","apr_ta") else None
    vf = args[-1] if args[-1] in ("all","apr","ta","apr_ta") else "apr_ta"
    result = change_shot_in_path(orig, shot, vf)
    sys.exit(0 if result else 2)
