"""
OGwiew — desktop OSINT workspace
Python 3.10+ | Standard library only (Tkinter is usually included with Python).

Privacy-first design:
- IP lookup uses ip-api.com for public IP metadata (internet required).
- Domain lookup performs DNS resolution only.
- Phone numbers are normalized/validated, not used to identify a person.
- Discord IDs are format-checked and optionally decoded to their approximate creation time.
- Username search opens public profile search URLs; it does not scrape accounts.
- No breach databases, credential lookup, private-account access, or covert collection.
"""

import json
import re
import socket
import threading
import urllib.parse
import urllib.request
import ipaddress
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_NAME = "OGwiew"
BG = "#090c12"
PANEL = "#101620"
PANEL2 = "#151e2b"
BORDER = "#263548"
TEXT = "#e7edf7"
MUTED = "#8e9bb0"
ACCENT = "#ff304f"
CYAN = "#4bd8d0"
GREEN = "#38d996"
FONT = ("Segoe UI", 10)
MONO = ("Consolas", 10)

CATEGORIES = [
    ("⌕", "Dashboard"),
    ("◎", "IP Lookup"),
    ("⌁", "Domain / DNS"),
    ("▣", "Phone Info"),
    ("◉", "Discord Lookup"),
    ("⌗", "Username Search"),
    ("✉", "Email Check"),
    ("↗", "URL Inspector"),
    ("⌖", "Geo Notes"),
    ("⌘", "Graph Builder"),
    ("✦", "OG AI Assistant"),
    ("▤", "Case Notes"),
]

class OGwiewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OGwiew | OSINT Workspace")
        self.root.geometry("1320x820")
        self.root.minsize(1040, 680)
        self.root.configure(bg=BG)
        self.nodes = []
        self.edges = []
        self.node_positions = {}
        self.dragging_node = None
        self.drag_offset = (0, 0)
        self.selected_category = "Dashboard"
        self.current_case = {"name": "Untitled case", "created": datetime.now().isoformat(timespec="seconds"), "notes": ""}
        self._setup_style()
        self._build_shell()
        self.show_category("Dashboard")

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground=PANEL2, background=PANEL2, foreground=TEXT)
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                        rowheight=28, bordercolor=BORDER)
        style.configure("Treeview.Heading", background=PANEL2, foreground=TEXT, relief="flat")
        style.map("Treeview", background=[("selected", "#26364a")], foreground=[("selected", TEXT)])

    def _label(self, parent, text, color=TEXT, size=10, bold=False):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=("Segoe UI", size, "bold" if bold else "normal"))

    def _button(self, parent, text, command, primary=False):
        return tk.Button(parent, text=text, command=command, cursor="hand2",
                         bg=ACCENT if primary else PANEL2, fg="#ffffff" if primary else TEXT,
                         activebackground="#d91f3b" if primary else "#26364a",
                         activeforeground="white", relief="flat", bd=0,
                         padx=13, pady=8, font=("Segoe UI", 9, "bold"))

    def _build_shell(self):
        self.sidebar = tk.Frame(self.root, bg="#080a0f", width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, bg="#080a0f")
        brand.pack(fill="x", padx=17, pady=(20, 20))
        tk.Label(brand, text="◈", fg=ACCENT, bg="#080a0f", font=("Segoe UI", 25, "bold")).pack(side="left")
        tk.Label(brand, text="OGwiew", fg=TEXT, bg="#080a0f", font=("Segoe UI", 19, "bold")).pack(side="left", padx=8)
        tk.Label(self.sidebar, text="OSINT WORKSPACE", bg="#080a0f", fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=19, pady=(0, 10))
        self.nav_buttons = {}
        for icon, name in CATEGORIES:
            b = tk.Button(self.sidebar, text=f"  {icon}   {name}", anchor="w",
                          command=lambda n=name: self.show_category(n),
                          bg="#080a0f", fg="#aeb9ca", activebackground="#241a24",
                          activeforeground="white", relief="flat", bd=0,
                          padx=14, pady=10, font=("Segoe UI", 10))
            b.pack(fill="x", padx=7, pady=1)
            self.nav_buttons[name] = b
        tk.Frame(self.sidebar, bg=BORDER, height=1).pack(fill="x", padx=14, pady=15)
        tk.Label(self.sidebar, text="LOCAL CASE FILE", bg="#080a0f", fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18)
        self.case_label = tk.Label(self.sidebar, text="Untitled case", bg="#080a0f", fg=CYAN,
                                   font=("Segoe UI", 9), wraplength=180, justify="left")
        self.case_label.pack(anchor="w", padx=18, pady=(6, 3))
        tk.Label(self.sidebar, text="v1.0  •  Privacy-first", bg="#080a0f", fg="#657186",
                 font=("Segoe UI", 8)).pack(side="bottom", anchor="w", padx=18, pady=15)

        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)
        top = tk.Frame(self.main, bg=BG)
        top.pack(fill="x", padx=25, pady=(19, 13))
        self.page_title = tk.Label(top, text="Dashboard", bg=BG, fg=TEXT, font=("Segoe UI", 21, "bold"))
        self.page_title.pack(side="left")
        self.status = tk.Label(top, text="● LOCAL WORKSPACE", bg=BG, fg=GREEN, font=("Segoe UI", 9, "bold"))
        self.status.pack(side="right", padx=8)
        tk.Frame(self.main, bg=BORDER, height=1).pack(fill="x", padx=25)
        self.content = tk.Frame(self.main, bg=BG)
        self.content.pack(fill="both", expand=True, padx=25, pady=20)

    def clear_content(self):
        for child in self.content.winfo_children():
            child.destroy()

    def card(self, parent, title, subtitle=None):
        frame = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        if title:
            tk.Label(frame, text=title, bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(
                anchor="w", padx=15, pady=(13, 2))
        if subtitle:
            tk.Label(frame, text=subtitle, bg=PANEL, fg=MUTED, font=FONT, wraplength=650,
                     justify="left").pack(anchor="w", padx=15, pady=(0, 10))
        return frame

    def show_category(self, name):
        self.selected_category = name
        self.page_title.config(text=name)
        for nav_name, button in self.nav_buttons.items():
            active = nav_name == name
            button.configure(bg="#2b1c25" if active else "#080a0f",
                             fg=ACCENT if active else "#aeb9ca",
                             font=("Segoe UI", 10, "bold" if active else "normal"))
        self.clear_content()
        handlers = {
            "Dashboard": self._dashboard,
            "IP Lookup": self._ip_lookup,
            "Domain / DNS": self._domain_lookup,
            "Phone Info": self._phone_info,
            "Discord Lookup": self._discord_lookup,
            "Username Search": self._username_search,
            "Email Check": self._email_check,
            "URL Inspector": self._url_inspector,
            "Geo Notes": self._geo_notes,
            "Graph Builder": self._graph_builder,
            "OG AI Assistant": self._og_ai_assistant,
            "Case Notes": self._case_notes,
        }
        handlers.get(name, self._dashboard)()

    def _dashboard(self):
        welcome = tk.Frame(self.content, bg=BG)
        welcome.pack(fill="x", pady=(0, 16))
        tk.Label(welcome, text="Map connections. Keep context.", bg=BG, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(welcome, text="A compact workspace for lawful, public-source research.",
                 bg=BG, fg=MUTED, font=FONT).pack(anchor="w", pady=(4, 0))
        stats = tk.Frame(self.content, bg=BG)
        stats.pack(fill="x", pady=(0, 15))
        for title, value, note, color in [
            ("GRAPH NODES", str(len(self.nodes)), "Entities in this case", CYAN),
            ("CONNECTIONS", str(len(self.edges)), "Relationships mapped", ACCENT),
            ("CASE STATUS", "LOCAL", "Saved on your computer", GREEN),
        ]:
            c = tk.Frame(stats, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
            c.pack(side="left", fill="both", expand=True, padx=(0, 10))
            tk.Label(c, text=title, bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(13, 4))
            tk.Label(c, text=value, bg=PANEL, fg=color, font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=14)
            tk.Label(c, text=note, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(0, 13))
        lower = tk.Frame(self.content, bg=BG)
        lower.pack(fill="both", expand=True)
        quick = self.card(lower, "QUICK ACTIONS", "Choose a module to start a lookup or organize a case.")
        quick.pack(side="left", fill="both", expand=True, padx=(0, 10))
        for label, target in [("⌁  IP address metadata", "IP Lookup"), ("▣  Phone number format", "Phone Info"),
                              ("◉  Discord ID tools", "Discord Lookup"), ("⌘  Build relationship graph", "Graph Builder")]:
            self._button(quick, label, lambda t=target: self.show_category(t)).pack(fill="x", padx=14, pady=5)
        info = self.card(lower, "BUILT FOR RESPONSIBLE OSINT",
                         "OGwiew focuses on public information and analyst notes. It does not access private accounts, expose a person's identity from a phone number, or query leaked credentials.")
        info.pack(side="left", fill="both", expand=True)
        self._button(info, "Open Case Notes", lambda: self.show_category("Case Notes")).pack(anchor="w", padx=14, pady=12)

    def _form_page(self, heading, description, field_label, placeholder, action_label, action):
        card = self.card(self.content, heading, description)
        card.pack(fill="x", anchor="n")
        form = tk.Frame(card, bg=PANEL)
        form.pack(fill="x", padx=15, pady=(2, 12))
        tk.Label(form, text=field_label, bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        entry = tk.Entry(form, bg=PANEL2, fg=TEXT, insertbackground=TEXT, relief="flat",
                         font=MONO, highlightthickness=1, highlightbackground=BORDER)
        entry.pack(fill="x", pady=(6, 12), ipady=9)
        entry.insert(0, placeholder)
        entry.bind("<FocusIn>", lambda e: entry.select_range(0, "end"))
        self._button(form, action_label, lambda: action(entry.get().strip()), True).pack(anchor="w")
        output_card = self.card(self.content, "RESULTS", "Results appear here. Network-based lookups require an internet connection.")
        output_card.pack(fill="both", expand=True, pady=(14, 0))
        output = tk.Text(output_card, bg="#0b1018", fg="#cbd6e7", insertbackground=TEXT,
                         relief="flat", font=MONO, wrap="word", height=10,
                         padx=12, pady=12)
        output.pack(fill="both", expand=True, padx=12, pady=(5, 12))
        output.insert("1.0", "Ready.\n")
        output.configure(state="disabled")
        def write(text):
            output.configure(state="normal")
            output.delete("1.0", "end")
            output.insert("1.0", str(text))
            output.configure(state="disabled")
        return entry, write

    def _ip_lookup(self):
        def lookup(value):
            try:
                ip = ipaddress.ip_address(value)
            except ValueError:
                write("Enter a valid IPv4 or IPv6 address.")
                return
            if not ip.is_global:
                write(f"Address: {ip}\nScope: {ipaddress.ip_address(value)}\n\nThis is not a public global IP address. Public geolocation lookup skipped.")
                return
            write("Looking up public IP metadata…")
            def task():
                try:
                    url = "http://ip-api.com/json/" + urllib.parse.quote(str(ip)) + "?fields=status,message,continent,country,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
                    req = urllib.request.Request(url, headers={"User-Agent": "OGwiew/1.0"})
                    with urllib.request.urlopen(req, timeout=8) as r:
                        data = json.loads(r.read().decode("utf-8"))
                    if data.get("status") != "success":
                        result = "Lookup failed: " + data.get("message", "unknown error")
                    else:
                        result = "PUBLIC IP METADATA\n" + "-" * 28 + "\n" + "\n".join(
                            f"{k}: {v}" for k, v in data.items() if k != "status")
                        result += "\n\nNote: IP geolocation is approximate and does not identify a household or person."
                    self.root.after(0, lambda: write(result))
                except Exception as e:
                    self.root.after(0, lambda: write(f"Lookup failed: {e}\nCheck your internet connection and try again."))
            threading.Thread(target=task, daemon=True).start()
        _, write = self._form_page("IP ADDRESS LOOKUP", "Fetch approximate public IP metadata. Private/reserved addresses are not sent to a lookup service.",
                                   "IPv4 / IPv6 address", "1.1.1.1", "LOOK UP IP", lookup)

    def _domain_lookup(self):
        def lookup(value):
            domain = value.replace("https://", "").replace("http://", "").split("/")[0].strip().rstrip(".")
            if not domain or " " in domain:
                write("Enter a domain such as example.com.")
                return
            try:
                results = socket.getaddrinfo(domain, None)
                ips = sorted({r[4][0] for r in results})
                write(f"DOMAIN: {domain}\nDNS RESOLUTION\n" + "-" * 28 + "\n" + "\n".join(ips) +
                      "\n\nThis checks DNS resolution only. It does not scan ports or test access.")
            except Exception as e:
                write(f"DNS lookup failed for {domain}\n{e}")
        self._form_page("DOMAIN / DNS", "Resolve a domain to its DNS addresses using your system resolver.",
                        "Domain", "example.com", "RESOLVE DNS", lookup)

    def _phone_info(self):
        def lookup(value):
            digits = re.sub(r"\D", "", value)
            if value.strip().startswith("+"):
                normalized = "+" + digits
            elif digits:
                normalized = digits
            else:
                normalized = ""
            if not (7 <= len(digits) <= 15):
                write("The number does not look like a plausible international number.\nTry including the country code, e.g. +420 123 456 789.")
                return
            write(f"INPUT: {value}\nNORMALIZED: {normalized}\nDIGITS: {len(digits)}\n\nThis is a basic format check only. It cannot reliably identify an owner, carrier, or live account.")
        self._form_page("PHONE INFO", "Normalize a phone number and check its rough length. No phone number is transmitted.",
                        "Phone number", "+420 123 456 789", "CHECK FORMAT", lookup)

    def _discord_lookup(self):
        def lookup(value):
            if not value.isdigit() or not (17 <= len(value) <= 20):
                write("Enter a numeric Discord user ID (typically 17–20 digits).\nYou can copy an ID in Discord with Developer Mode enabled.")
                return
            try:
                timestamp = (int(value) >> 22) + 1420070400000
                dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
                if dt.year < 2015 or dt > datetime.now(timezone.utc):
                    raise ValueError()
                result = f"DISCORD SNOWFLAKE\n{'-'*28}\nID: {value}\nApproximate creation time (UTC): {dt.isoformat()}\n\nA snowflake ID encodes a timestamp. This does not reveal the account owner's real identity or private information."
            except Exception:
                result = "The value has the right shape, but its timestamp could not be interpreted as a plausible Discord snowflake."
            write(result)
        self._form_page("DISCORD LOOKUP", "Validate a Discord ID and decode its approximate creation timestamp locally.",
                        "Discord user / message ID", "123456789012345678", "DECODE ID", lookup)

    def _username_search(self):
        def lookup(value):
            if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", value):
                write("Use a username with letters, numbers, dots, underscores or hyphens.")
                return
            sites = [
                ("GitHub", f"https://github.com/{value}"),
                ("Reddit", f"https://www.reddit.com/user/{value}/"),
                ("GitLab", f"https://gitlab.com/{value}"),
                ("YouTube search", "https://www.youtube.com/results?search_query=" + urllib.parse.quote(value)),
                ("Google search", "https://www.google.com/search?q=" + urllib.parse.quote('"' + value + '"')),
            ]
            for name, url in sites:
                self.add_node(name, value, "Public profile/search link")
            write("PUBLIC SEARCH LINKS\n" + "-" * 28 + "\n" + "\n".join(f"{name}: {url}" for name, url in sites) +
                  "\n\nLinks are provided for manual review. OGwiew does not scrape profiles or confirm that accounts belong to the same person.")
        self._form_page("USERNAME SEARCH", "Create public profile/search links for manual review. A matching username is not proof of identity.",
                        "Username / handle", "example_user", "CREATE SEARCH LINKS", lookup)

    def _email_check(self):
        def lookup(value):
            if len(value) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
                write("The value does not match a basic email-address pattern.")
            else:
                write(f"FORMAT: plausible\nADDRESS: {value}\n\nNo message was sent and no mailbox, owner, or breach database was queried.")
        self._form_page("EMAIL CHECK", "Check syntax only. This does not verify whether a mailbox exists.",
                        "Email address", "name@example.com", "CHECK FORMAT", lookup)

    def _url_inspector(self):
        def lookup(value):
            from urllib.parse import urlparse
            candidate = value if "://" in value else "https://" + value
            parsed = urlparse(candidate)
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                write("Enter a valid http(s) URL.")
                return
            host = parsed.hostname
            warnings = []
            if "@" in parsed.netloc:
                warnings.append("URL contains user-info before the host; check carefully.")
            if host.startswith("xn--") or ".xn--" in host:
                warnings.append("Internationalized/punycode hostname: visually inspect for lookalikes.")
            if parsed.scheme != "https":
                warnings.append("The URL uses HTTP rather than HTTPS.")
            write(f"URL: {candidate}\nScheme: {parsed.scheme}\nHost: {host}\nPort: {parsed.port or 'default'}\nPath: {parsed.path or '/'}\nQuery present: {'yes' if parsed.query else 'no'}\n\nNOTES\n" + ("\n".join('• ' + x for x in warnings) if warnings else "No basic syntax warning detected.") +
                  "\n\nThis is a static check, not a malware verdict. Do not open suspicious links on your main device.")
        self._form_page("URL INSPECTOR", "Inspect URL structure locally without visiting the target site.",
                        "URL", "https://example.com/path", "INSPECT URL", lookup)

    def _geo_notes(self):
        card = self.card(self.content, "GEO NOTES", "Record coordinates you already have permission to use. No tracking or live location collection.")
        card.pack(fill="x")
        fields = tk.Frame(card, bg=PANEL)
        fields.pack(fill="x", padx=15, pady=10)
        entries = []
        for label, placeholder in [("Latitude", "50.0755"), ("Longitude", "14.4378"), ("Label / source", "Public landmark")]:
            tk.Label(fields, text=label, bg=PANEL, fg=MUTED).pack(anchor="w", pady=(5, 2))
            e = tk.Entry(fields, bg=PANEL2, fg=TEXT, insertbackground=TEXT, relief="flat")
            e.pack(fill="x", ipady=7)
            e.insert(0, placeholder)
            entries.append(e)
        def save():
            try:
                lat, lon = float(entries[0].get()), float(entries[1].get())
                if not -90 <= lat <= 90 or not -180 <= lon <= 180:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Invalid coordinates", "Latitude must be -90..90 and longitude -180..180.")
                return
            self.add_node("Location", entries[2].get(), f"{lat}, {lon}")
            messagebox.showinfo("Added", "Location note added to the relationship graph.")
        self._button(card, "ADD LOCATION TO GRAPH", save, True).pack(anchor="w", padx=15, pady=(0, 15))

    def _graph_builder(self):
        outer = tk.Frame(self.content, bg=BG)
        outer.pack(fill="both", expand=True)
        controls = tk.Frame(outer, bg=PANEL, width=265, highlightbackground=BORDER, highlightthickness=1)
        controls.pack(side="left", fill="y", padx=(0, 12))
        controls.pack_propagate(False)
        tk.Label(controls, text="ADD ENTITY", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=13, pady=(14, 10))
        inputs = {}
        for label, default in [("Type", "Person / account"), ("Name / label", "New entity"), ("Details / source", "Public source or analyst note")]:
            tk.Label(controls, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=13, pady=(4, 3))
            e = tk.Entry(controls, bg=PANEL2, fg=TEXT, insertbackground=TEXT, relief="flat")
            e.pack(fill="x", padx=13, ipady=7)
            e.insert(0, default)
            inputs[label] = e
        self._label(controls, "Connect node numbers (e.g. 1 and 2)", MUTED, 9).pack(anchor="w", padx=13, pady=(17, 4))
        linkrow = tk.Frame(controls, bg=PANEL)
        linkrow.pack(fill="x", padx=13)
        a = tk.Entry(linkrow, bg=PANEL2, fg=TEXT, width=7, relief="flat")
        a.pack(side="left", ipady=6)
        b = tk.Entry(linkrow, bg=PANEL2, fg=TEXT, width=7, relief="flat")
        b.pack(side="left", padx=6, ipady=6)
        self._button(controls, "＋ ADD NODE", lambda: self.add_node(inputs["Type"].get(), inputs["Name / label"].get(), inputs["Details / source"].get())).pack(fill="x", padx=13, pady=(12, 5))
        self._button(controls, "⤳ CONNECT NODES", lambda: self.connect_nodes(a.get(), b.get()), True).pack(fill="x", padx=13, pady=5)
        self._button(controls, "✦ ASK OG AI ABOUT CASE", lambda: self.show_category("OG AI Assistant")).pack(fill="x", padx=13, pady=5)
        self._button(controls, "EXPORT CASE JSON", self.export_case).pack(fill="x", padx=13, pady=5)
        self._button(controls, "CLEAR GRAPH", self.clear_graph).pack(fill="x", padx=13, pady=5)
        tk.Label(controls, text="TIP: drag a node to move it.\nConnections follow automatically.", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8), justify="left").pack(anchor="w", padx=13, pady=(12, 0))

        graphpanel = tk.Frame(outer, bg="#080c13", highlightbackground=BORDER, highlightthickness=1)
        graphpanel.pack(side="left", fill="both", expand=True)
        top = tk.Frame(graphpanel, bg="#080c13")
        top.pack(fill="x", padx=12, pady=10)
        tk.Label(top, text="RELATIONSHIP MAP", bg="#080c13", fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(top, text="● entity    ⤳ relationship", bg="#080c13", fg=MUTED, font=("Segoe UI", 9)).pack(side="right")
        self.graph_canvas = tk.Canvas(graphpanel, bg="#080c13", highlightthickness=0, cursor="hand2")
        self.graph_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        self.graph_canvas.bind("<Configure>", lambda e: self.draw_graph())
        self.graph_canvas.bind("<Button-1>", self._graph_mouse_down)
        self.graph_canvas.bind("<B1-Motion>", self._graph_mouse_move)
        self.graph_canvas.bind("<ButtonRelease-1>", self._graph_mouse_up)
        self.draw_graph()

    def _graph_mouse_down(self, event):
        if not self.nodes:
            return
        closest = self.graph_canvas.find_closest(event.x, event.y)
        tags = self.graph_canvas.gettags(closest[0]) if closest else ()
        node_id = next((int(tag.split("_", 1)[1]) for tag in tags
                        if tag.startswith("node_") and tag.split("_", 1)[1].isdigit()), None)
        if node_id is None:
            # Also allow grabbing a node by clicking near its center.
            for node in self.nodes:
                pos = self.node_positions.get(node["id"])
                if pos and (pos[0] - event.x) ** 2 + (pos[1] - event.y) ** 2 <= 28 ** 2:
                    node_id = node["id"]
                    break
        if node_id is not None and node_id in self.node_positions:
            self.dragging_node = node_id
            x, y = self.node_positions[node_id]
            self.drag_offset = (x - event.x, y - event.y)

    def _graph_mouse_move(self, event):
        if self.dragging_node is None:
            return
        w = max(self.graph_canvas.winfo_width(), 100)
        h = max(self.graph_canvas.winfo_height(), 100)
        x = min(max(24, event.x + self.drag_offset[0]), w - 24)
        y = min(max(24, event.y + self.drag_offset[1]), h - 45)
        self.node_positions[self.dragging_node] = (x, y)
        self.draw_graph()

    def _graph_mouse_up(self, event):
        self.dragging_node = None

    def add_node(self, kind, name, details=""):
        name = name.strip() or "Unnamed entity"
        self.nodes.append({"id": len(self.nodes) + 1, "type": kind.strip(), "name": name, "details": details.strip()})
        self._refresh_sidebar_case()
        if self.selected_category == "Graph Builder":
            self.draw_graph()

    def connect_nodes(self, first, second):
        try:
            a, b = int(first), int(second)
            valid = {n["id"] for n in self.nodes}
            if a == b or a not in valid or b not in valid:
                raise ValueError()
            if not any({e["from"], e["to"]} == {a, b} for e in self.edges):
                self.edges.append({"from": a, "to": b, "label": "related"})
            self.draw_graph()
        except ValueError:
            messagebox.showerror("Cannot connect", "Enter two different existing node numbers, such as 1 and 2.")

    def draw_graph(self):
        if not hasattr(self, "graph_canvas") or not self.graph_canvas.winfo_exists():
            return
        c = self.graph_canvas
        c.delete("all")
        w, h = max(c.winfo_width(), 400), max(c.winfo_height(), 300)
        for x in range(0, w, 24):
            for y in range(0, h, 24):
                c.create_oval(x, y, x+1.5, y+1.5, fill="#253041", outline="")
        if not self.nodes:
            c.create_text(w/2, h/2, text="Add an entity to begin mapping connections", fill="#738198",
                          font=("Segoe UI", 12))
            return

        import math
        n = len(self.nodes)
        cx, cy = w / 2, h / 2
        radius = min(w, h) * (0.34 if n > 2 else 0.22)
        for i, node in enumerate(self.nodes):
            node_id = node["id"]
            if node_id not in self.node_positions:
                angle = -math.pi / 2 + 2 * math.pi * i / max(n, 1)
                self.node_positions[node_id] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))

        # Draw connections first so they sit behind the nodes.
        for edge in self.edges:
            if edge["from"] not in self.node_positions or edge["to"] not in self.node_positions:
                continue
            x1, y1 = self.node_positions[edge["from"]]
            x2, y2 = self.node_positions[edge["to"]]
            dx, dy = x2 - x1, y2 - y1
            length = max(math.hypot(dx, dy), 1)
            bend = min(32, length * 0.12)
            mx, my = (x1+x2)/2 - dy/length*bend, (y1+y2)/2 + dx/length*bend
            c.create_line(x1, y1, mx, my, x2, y2, fill=ACCENT, width=2,
                          smooth=True, splinesteps=18, arrow="last", arrowshape=(8, 10, 4),
                          tags=("edge",))
            c.create_text(mx, my-9, text=edge.get("label", "related"), fill="#ff8494",
                          font=("Segoe UI", 8), tags=("edge",))

        for node in self.nodes:
            x, y = self.node_positions[node["id"]]
            tags = ("node", f"node_{node['id']}")
            c.create_oval(x-20, y-20, x+20, y+20, fill="#172a3b", outline=CYAN, width=2, tags=tags)
            c.create_text(x, y, text=str(node["id"]), fill=TEXT, font=("Segoe UI", 10, "bold"), tags=tags)
            label = node["name"][:24]
            c.create_text(x, y+30, text=label, fill="#dce5f3", font=("Segoe UI", 9), tags=tags)
            c.create_text(x, y+43, text=node["type"][:20], fill="#7f91a9", font=("Segoe UI", 7), tags=tags)
        c.create_text(12, h-12, anchor="sw", text=f"{len(self.nodes)} entities  •  {len(self.edges)} connections  •  drag nodes to reposition",
                      fill="#6f7e93", font=("Consolas", 9))

    def clear_graph(self):
        if messagebox.askyesno("Clear graph", "Remove all graph nodes and connections from this case?"):
            self.nodes.clear()
            self.edges.clear()
            self.node_positions.clear()
            self.draw_graph()
            self._refresh_sidebar_case()

    def export_case(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("OGwiew case", "*.json"), ("All files", "*.*")])
        if not path:
            return
        data = {"app": APP_NAME, "version": 1, "case": self.current_case, "nodes": self.nodes, "edges": self.edges, "node_positions": self.node_positions}
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Export complete", f"Case exported to:\n{path}")
        except OSError as e:
            messagebox.showerror("Export failed", str(e))

    def _og_ai_assistant(self):
        card = self.card(self.content, "✦ OG AI — CASE ASSISTANT",
                         "Ask for a case summary, graph interpretation, or a sensible next-step checklist. If OPENAI_API_KEY is configured in your environment, requests can be sent to OpenAI; otherwise OG AI runs in local offline helper mode.")
        card.pack(fill="both", expand=True)
        tk.Label(card, text="YOUR QUESTION", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
        question = tk.Text(card, bg="#0b1018", fg=TEXT, insertbackground=TEXT, relief="flat",
                           height=4, font=FONT, wrap="word")
        question.pack(fill="x", padx=14)
        question.insert("1.0", "Summarize my graph and suggest responsible next steps.")
        output = tk.Text(card, bg="#0b1018", fg="#cbd6e7", insertbackground=TEXT, relief="flat",
                         font=MONO, wrap="word", height=14, padx=12, pady=12)
        output.pack(fill="both", expand=True, padx=14, pady=12)
        output.insert("1.0", "OG AI ready. Ask a question to get started.\n")
        def show_result(text):
            output.configure(state="normal")
            output.delete("1.0", "end")
            output.insert("1.0", text)
            output.configure(state="disabled")
        def ask():
            prompt = question.get("1.0", "end-1c").strip()
            if not prompt:
                show_result("Type a question first.")
                return
            case_data = {
                "case": self.current_case.get("name", "Untitled case"),
                "nodes": self.nodes,
                "connections": self.edges,
                "notes": self.current_case.get("notes", "")
            }
            context = json.dumps(case_data, ensure_ascii=False, indent=2)
            show_result("OG AI is preparing an answer…")
            def worker():
                import os
                api_key = os.environ.get("OPENAI_API_KEY", "").strip()
                if api_key:
                    try:
                        payload = {
                            "model": os.environ.get("OGWIEW_AI_MODEL", "gpt-4.1-mini"),
                            "messages": [
                                {"role": "system", "content": (
                                    "You are OG AI, a careful OSINT research assistant. Help with public-source "
                                    "research, graph organization, uncertainty, source validation, and privacy-respecting "
                                    "next steps. Never claim a link proves two accounts share an owner. Do not help "
                                    "doxx, stalk, access private accounts, obtain credentials, or identify a private "
                                    "person from a phone number. Be clear about uncertainty. Case data follows."
                                )},
                                {"role": "user", "content": "Case data (treat as unverified notes):\n" + context +
                                 "\n\nQuestion:\n" + prompt}
                            ],
                            "temperature": 0.3
                        }
                        req = urllib.request.Request(
                            "https://api.openai.com/v1/chat/completions",
                            data=json.dumps(payload).encode("utf-8"),
                            headers={"Authorization": "Bearer " + api_key,
                                     "Content-Type": "application/json"},
                            method="POST"
                        )
                        with urllib.request.urlopen(req, timeout=45) as response:
                            result = json.loads(response.read().decode("utf-8"))
                        answer = result["choices"][0]["message"]["content"].strip()
                        answer = "OG AI • ONLINE MODE\n\n" + answer
                    except Exception as exc:
                        answer = ("Online AI request failed: " + str(exc) +
                                  "\n\nCheck your API key, account access, model setting, and connection.")
                else:
                    q = prompt.lower()
                    lines = [
                        "OG AI • OFFLINE HELPER MODE",
                        "",
                        f"Case: {case_data['case']}",
                        f"Entities: {len(self.nodes)}",
                        f"Connections: {len(self.edges)}",
                        ""
                    ]
                    if any(word in q for word in ("summar", "graph", "case", "overview", "connection")):
                        if self.nodes:
                            lines.append("ENTITIES")
                            lines.extend(f"  #{n['id']} [{n['type']}] {n['name']} — {n.get('details', '')}"
                                         for n in self.nodes)
                        else:
                            lines.append("The graph is empty. Add entities in Graph Builder first.")
                        if self.edges:
                            lines.append("\nCONNECTIONS")
                            lines.extend(f"  #{e['from']} ↔ #{e['to']} ({e.get('label', 'related')})"
                                         for e in self.edges)
                        else:
                            lines.append("\nNo relationships have been added yet.")
                    lines.extend([
                        "\nSUGGESTED WORKFLOW",
                        "1. Record where each fact came from and when it was checked.",
                        "2. Separate verified facts from hypotheses; mark confidence explicitly.",
                        "3. Use a connection only when you can explain its evidence.",
                        "4. Corroborate important claims with an independent public source.",
                        "5. Avoid collecting sensitive personal details that are not needed.",
                        "",
                        "Offline mode uses built-in rules and does not call a language model. To enable online AI, "
                        "set OPENAI_API_KEY in your environment before launching OGwiew. Online prompts include "
                        "the current case nodes, connections, and notes, so only send information you are allowed to share."
                    ])
                    answer = "\n".join(lines)
                self.root.after(0, lambda result=answer: show_result(result))
            threading.Thread(target=worker, daemon=True).start()
        self._button(card, "✦ ASK OG AI", ask, True).pack(anchor="w", padx=14, pady=(0, 14))
        tk.Label(card, text="Online mode may send case context to the configured AI provider. Offline mode stays local.",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 8), wraplength=750, justify="left").pack(anchor="w", padx=14, pady=(0, 12))

    def _case_notes(self):
        card = self.card(self.content, "CASE NOTES", "Notes are kept in memory until you export the case JSON.")
        card.pack(fill="both", expand=True)
        tk.Label(card, text="Case name", bg=PANEL, fg=MUTED).pack(anchor="w", padx=14, pady=(10, 3))
        name = tk.Entry(card, bg=PANEL2, fg=TEXT, insertbackground=TEXT, relief="flat")
        name.pack(fill="x", padx=14, ipady=8)
        name.insert(0, self.current_case["name"])
        tk.Label(card, text="Analyst notes", bg=PANEL, fg=MUTED).pack(anchor="w", padx=14, pady=(12, 3))
        notes = tk.Text(card, bg="#0b1018", fg=TEXT, insertbackground=TEXT, relief="flat", height=12, font=MONO)
        notes.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        notes.insert("1.0", self.current_case.get("notes", ""))
        def save():
            self.current_case["name"] = name.get().strip() or "Untitled case"
            self.current_case["notes"] = notes.get("1.0", "end-1c")
            self._refresh_sidebar_case()
            messagebox.showinfo("Saved", "Notes saved in the current session. Use Graph Builder → Export Case JSON to keep a copy.")
        self._button(card, "SAVE NOTES", save, True).pack(anchor="w", padx=14, pady=(0, 14))

    def _refresh_sidebar_case(self):
        if hasattr(self, "case_label"):
            self.case_label.configure(text=self.current_case.get("name", "Untitled case"))

if __name__ == "__main__":
    root = tk.Tk()
    app = OGwiewApp(root)
    root.mainloop()
