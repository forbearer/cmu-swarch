#!/usr/bin/env python3
"""
Renders a Garlan-style component-and-connector diagram as a standalone SVG, from the same
component/port/connector data each architecture/*.sysml file encodes textually. The .sysml file
is the source of truth; this is a companion visualization of it, not a generator of it -- keep
them in sync by hand when either changes (same pattern already used for the project's SysML v2
workflow diagrams elsewhere in Owen's other repos).

No external dependencies: pure stdlib, writes a single self-contained .svg file.
"""
import argparse
import json

BOX_W, BOX_H = 200, 110
GAP_X = 110
MARGIN_X, MARGIN_Y = 60, 90
PORT_SIZE = 10

CONNECTOR_STYLES = {
  "ProcedureCallConnector": {"color": "#2b2b2b", "dash": "none", "label": "procedure call"},
  "PublishSubscribeConnector": {"color": "#1f6feb", "dash": "none", "label": "publish-subscribe (cereal)"},
  "StreamConnector": {"color": "#1a7f37", "dash": "none", "label": "event stream (WebSocket)"},
  "RepositoryConnector": {"color": "#6e7781", "dash": "6,4", "label": "repository (file on disk)"},
  "RequestReplyConnector": {"color": "#bf8700", "dash": "none", "label": "request-reply (HTTP)"},
}


def layout(components):
  x = MARGIN_X
  positions = {}
  for c in components:
    positions[c["id"]] = {"x": x, "y": MARGIN_Y, "w": BOX_W, "h": BOX_H}
    x += BOX_W + GAP_X
  return positions, x - GAP_X + MARGIN_X


def port_point(positions, comp_id, side, offset=0):
  p = positions[comp_id]
  if side == "left":
    return p["x"], p["y"] + p["h"] / 2 + offset
  if side == "right":
    return p["x"] + p["w"], p["y"] + p["h"] / 2 + offset
  if side == "top":
    return p["x"] + p["w"] / 2 + offset, p["y"]
  return p["x"] + p["w"] / 2 + offset, p["y"] + p["h"]  # bottom


def esc(s):
  return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wrap(text, width=26):
  words, lines, cur = text.split(), [], ""
  for w in words:
    if len(cur) + len(w) + 1 <= width:
      cur = (cur + " " + w).strip()
    else:
      lines.append(cur)
      cur = w
  if cur:
    lines.append(cur)
  return lines


def render(title, components, connectors, out_path):
  positions, total_w = layout(components)
  total_h = MARGIN_Y + BOX_H + 260

  svg = []
  svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w} {total_h}" '
             f'font-family="Menlo, Consolas, monospace">')
  svg.append(f'<rect width="{total_w}" height="{total_h}" fill="#ffffff"/>')
  svg.append(f'<text x="{total_w/2}" y="36" text-anchor="middle" font-size="20" font-weight="bold" '
             f'fill="#1a1a1a">{esc(title)}</text>')

  svg.append('<defs>')
  for ctype, style in CONNECTOR_STYLES.items():
    svg.append(f'<marker id="arrow-{ctype}" viewBox="0 0 10 10" refX="9" refY="5" '
               f'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
               f'<path d="M0,0 L10,5 L0,10 z" fill="{style["color"]}"/></marker>')
  svg.append('</defs>')

  def unpack(end):
    return (end[0], end[1], end[2] if len(end) > 2 else 0)

  # connectors first, so they sit behind the component boxes
  conn_label_y = total_h - 190
  for i, conn in enumerate(connectors):
    style = CONNECTOR_STYLES[conn["type"]]
    from_id, from_side, from_off = unpack(conn["from"])
    to_id, to_side, to_off = unpack(conn["to"])
    x1, y1 = port_point(positions, from_id, from_side, from_off)
    x2, y2 = port_point(positions, to_id, to_side, to_off)
    svg.append(f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{style["color"]}" '
               f'stroke-width="2.5" stroke-dasharray="{style["dash"]}" '
               f'marker-end="url(#arrow-{conn["type"]})"/>')
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - 10
    svg.append(f'<rect x="{mx - len(conn["label"]) * 3.3 - 4}" y="{my - 14}" '
               f'width="{len(conn["label"]) * 6.6 + 8}" height="18" fill="#ffffff" opacity="0.9"/>')
    svg.append(f'<text x="{mx}" y="{my}" text-anchor="middle" font-size="12" '
               f'fill="{style["color"]}">{esc(conn["label"])}</text>')

  # component boxes + ports
  for c in components:
    p = positions[c["id"]]
    svg.append(f'<rect x="{p["x"]}" y="{p["y"]}" width="{p["w"]}" height="{p["h"]}" rx="6" '
               f'fill="#f6f8fa" stroke="#1a1a1a" stroke-width="2"/>')
    svg.append(f'<text x="{p["x"] + p["w"]/2}" y="{p["y"] + 24}" text-anchor="middle" '
               f'font-size="13" font-weight="bold" fill="#1a1a1a">{esc(c["name"])}</text>')
    lines = wrap(c.get("subtitle", ""), 24)
    for i, line in enumerate(lines[:4]):
      svg.append(f'<text x="{p["x"] + p["w"]/2}" y="{p["y"] + 44 + i*14}" text-anchor="middle" '
                 f'font-size="10" fill="#57606a">{esc(line)}</text>')
    # ports: small squares where this component's connectors attach
    for conn in connectors:
      for end in (conn["from"], conn["to"]):
        eid, eside, eoff = unpack(end)
        if eid == c["id"]:
          px, py = port_point(positions, c["id"], eside, eoff)
          svg.append(f'<rect x="{px - PORT_SIZE/2}" y="{py - PORT_SIZE/2}" '
                     f'width="{PORT_SIZE}" height="{PORT_SIZE}" fill="#1a1a1a"/>')

  # legend
  legend_y = total_h - 150
  svg.append(f'<text x="{MARGIN_X}" y="{legend_y}" font-size="13" font-weight="bold" '
             f'fill="#1a1a1a">Connector types (Garlan C&amp;C style)</text>')
  used_types = {c["type"] for c in connectors}
  ly = legend_y + 22
  for ctype in CONNECTOR_STYLES:
    if ctype not in used_types:
      continue
    style = CONNECTOR_STYLES[ctype]
    svg.append(f'<line x1="{MARGIN_X}" y1="{ly}" x2="{MARGIN_X+40}" y2="{ly}" '
               f'stroke="{style["color"]}" stroke-width="2.5" stroke-dasharray="{style["dash"]}"/>')
    svg.append(f'<text x="{MARGIN_X+50}" y="{ly+4}" font-size="12" fill="#1a1a1a">'
               f'{ctype} &#8212; {esc(style["label"])}</text>')
    ly += 20

  svg.append('</svg>')

  with open(out_path, "w") as f:
    f.write("\n".join(svg))
  print(f"wrote {out_path}")


def main():
  p = argparse.ArgumentParser()
  p.add_argument("spec", help="JSON file with title/components/connectors")
  p.add_argument("out", help="output .svg path")
  args = p.parse_args()
  with open(args.spec) as f:
    spec = json.load(f)
  render(spec["title"], spec["components"], spec["connectors"], args.out)


if __name__ == "__main__":
  main()
