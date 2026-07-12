#!/usr/bin/env python3
import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def cleanup_root(svg: ET.Element) -> None:
    svg.attrib.pop("style", None)
    if svg.attrib.get("preserveAspectRatio") == "none":
        svg.attrib["preserveAspectRatio"] = "xMidYMid meet"


def cleanup_defs(svg: ET.Element) -> None:
    for el in svg.iter():
        ln = local_name(el.tag)
        if ln == "stop":
            el.attrib.pop("class", None)
        el.attrib.pop("style", None)


def assign_shape_ids(svg: ET.Element, prefix: str = "shape") -> None:
    i = 1
    for el in svg.iter():
        if local_name(el.tag) == "path":
            if "id" not in el.attrib:
                el.attrib["id"] = f"{prefix}_{i:03d}"
            i += 1


def reorder_root_attrs(svg_text: str) -> str:
    m = re.search(r"<svg\s+([^>]+)>", svg_text)
    if not m:
        return svg_text
    attrs = m.group(1)
    pairs = re.findall(r'([:\w-]+)="([^"]*)"', attrs)
    wanted_order = ["xmlns", "viewBox", "width", "height", "preserveAspectRatio"]
    kv = {k: v for k, v in pairs}

    ordered = []
    for k in wanted_order:
        if k in kv:
            ordered.append(f'{k}="{kv.pop(k)}"')
    for k in sorted(kv.keys()):
        ordered.append(f'{k}="{kv[k]}"')

    new_open = "<svg " + " ".join(ordered) + ">"
    return svg_text[: m.start()] + new_open + svg_text[m.end():]


def run(src: Path, dst: Path) -> None:
    tree = ET.parse(src)
    root = tree.getroot()

    cleanup_root(root)
    cleanup_defs(root)
    assign_shape_ids(root)

    xml = ET.tostring(root, encoding="unicode")
    xml = reorder_root_attrs(xml)
    xml = xml.replace("><", ">\n<") + "\n"
    dst.write_text(xml, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare SVG for Lottie animation workflow")
    parser.add_argument("src", type=Path, help="Input SVG")
    parser.add_argument("dst", type=Path, help="Output SVG")
    args = parser.parse_args()
    run(args.src, args.dst)
