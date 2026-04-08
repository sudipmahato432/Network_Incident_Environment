import shlex

class MockServerState:
    def __init__(self, task_level: str):
        self.task_level = task_level.lower()
        
        # Virtual Environment Variables
        self.pwd = "/root"
        
        # Default Healthy State
        self.files = {
            "/etc/nginx/nginx.conf": "server {\n    listen 80;\n    server_name localhost;\n}",
            "/var/log/syslog": "System booted cleanly.\n"
        }
        self.services = {"nginx": "active"}
        self.routes = {"10.0.2.0/24": "10.0.0.1"} # Correct gateway
        self.firewall_rules = [] # Empty means allow all
        
        # Grader Tracking (to award partial points later)
        self.diagnostics_run = []
        
        # --- APPLY BUGS BASED ON TASK LEVEL ---
        self._inject_bugs()

    def _inject_bugs(self):
        """Injects the specific failure condition for the current task."""
        if self.task_level == "easy":
            # Bug: Typo in Nginx Config
            self.files["/etc/nginx/nginx.conf"] = "server {\n    listen 800;\n    server_name localhost;\n}"
            self.files["/var/log/syslog"] += "nginx: [emerg] invalid port in /etc/nginx/nginx.conf\n"
            self.services["nginx"] = "failed"
            
        elif self.task_level == "medium":
            # Bug: Rogue iptables rule blocking the database
            self.firewall_rules.append("-A INPUT -s 10.0.1.5 -j DROP")
            self.files["/var/log/syslog"] += "AppError: Connection timeout to DB at 10.0.1.5\n"
            
        elif self.task_level == "hard":
            # Bug: Asymmetric/Wrong routing for the 10.0.2.0/24 subnet
            self.routes["10.0.2.0/24"] = "192.168.1.99" # Dead gateway
            self.files["/var/log/syslog"] += "NetError: Destination host unreachable for 10.0.2.0/24\n"

    def execute(self, cmd: str) -> tuple[str, str, int]:
        """
        Parses the command and returns (stdout, stderr, exit_code).
        """
        if not cmd.strip():
            return "", "", 0

        # Handle file writing via echo "content" > file
        if ">" in cmd and "echo" in cmd:
            return self._handle_echo_write(cmd)

        try:
            parts = shlex.split(cmd)
        except ValueError as e:
            return "", f"bash: syntax error: {str(e)}", 1
            
        base_cmd = parts[0]

        if base_cmd == "cat":
            return self._handle_cat(parts)
        elif base_cmd == "systemctl":
            return self._handle_systemctl(parts)
        elif base_cmd == "ping":
            return self._handle_ping(parts)
        elif base_cmd == "iptables":
            return self._handle_iptables(parts)
        elif base_cmd == "ip":
            return self._handle_ip(parts)
        else:
            return "", f"bash: {base_cmd}: command not found", 127

    # --- VIRTUAL COMMAND IMPLEMENTATIONS ---

    def _handle_echo_write(self, cmd: str) -> tuple[str, str, int]:
        """Allows the agent to overwrite files. e.g., echo "listen 80;" > /etc/nginx/nginx.conf"""
        try:
            content_part, file_part = cmd.split(">", 1)
            content = content_part.replace("echo", "").strip().strip('"').strip("'")
            filename = file_part.strip()
            self.files[filename] = content
            return "", "", 0
        except Exception:
            return "", "bash: syntax error near unexpected token `>'", 1

    def _handle_cat(self, parts: list[str]) -> tuple[str, str, int]:
        if len(parts) < 2:
            return "", "cat: missing operand", 1
        filename = parts[1]
        
        if "syslog" in filename:
            self.diagnostics_run.append("read_logs")
            
        if filename in self.files:
            return self.files[filename], "", 0
        return "", f"cat: {filename}: No such file or directory", 1

    def _handle_systemctl(self, parts: list[str]) -> tuple[str, str, int]:
        if len(parts) < 3:
            return "", "systemctl: missing arguments", 1
        action, service = parts[1], parts[2]
        
        if service != "nginx":
            return "", f"Unit {service}.service could not be found.", 4

        if action == "status":
            self.diagnostics_run.append("checked_service")
            status = self.services["nginx"]
            return f"● nginx.service - A high performance web server\n   Active: {status}", "", 0
            
        elif action == "restart":
            # Check if config is fixed
            if "listen 80;" in self.files.get("/etc/nginx/nginx.conf", ""):
                self.services["nginx"] = "active"
                return "", "", 0
            else:
                self.services["nginx"] = "failed"
                return "", "Job for nginx.service failed because the control process exited with error code.", 1
                
        return "", f"Unknown systemctl action: {action}", 1

    def _handle_ping(self, parts: list[str]) -> tuple[str, str, int]:
        target = parts[-1]
        self.diagnostics_run.append("pinged")
        
        # Medium Task Check: Blocked by firewall?
        if target == "10.0.1.5" and any("DROP" in rule for rule in self.firewall_rules):
            return "", f"PING {target} ({target}) 56(84) bytes of data.\n100% packet loss.", 1
            
        # Hard Task Check: Blocked by routing?
        if target.startswith("10.0.2.") and self.routes.get("10.0.2.0/24") != "10.0.0.1":
            return "", f"From 192.168.1.99 icmp_seq=1 Destination Host Unreachable", 1
            
        return f"PING {target} ({target}) 56(84) bytes of data.\n64 bytes from {target}: icmp_seq=1 ttl=64 time=0.034 ms", "", 0

    def _handle_iptables(self, parts: list[str]) -> tuple[str, str, int]:
        self.diagnostics_run.append("checked_firewall")
        if "-L" in parts:
            output = "Chain INPUT (policy ACCEPT)\ntarget     prot opt source               destination\n"
            for rule in self.firewall_rules:
                if "DROP" in rule:
                     output += "DROP       all  --  10.0.1.5             0.0.0.0/0\n"
            return output, "", 0
            
        if "-D" in parts or "-F" in parts: # Delete or Flush
            self.firewall_rules = []
            return "", "", 0
            
        return "", "iptables: invalid option", 1

    def _handle_ip(self, parts: list[str]) -> tuple[str, str, int]:
        if len(parts) > 1 and parts[1] == "route":
            self.diagnostics_run.append("checked_routes")
            
            # Agent is deleting the bad route
            if "del" in parts:
                self.routes.pop("10.0.2.0/24", None)
                return "", "", 0
                
            # Agent is adding the correct route
            if "add" in parts:
                try:
                    subnet = parts[parts.index("add") + 1]
                    gw = parts[parts.index("via") + 1]
                    self.routes[subnet] = gw
                    return "", "", 0
                except (ValueError, IndexError):
                    return "", "Error: RTNETLINK answers: Invalid argument", 1
                    
            # Just viewing the routes
            output = "default via 10.0.0.1 dev eth0\n"
            for subnet, gw in self.routes.items():
                output += f"{subnet} via {gw} dev eth1\n"
            return output, "", 0
            
        return "", "Object \"ip\" is unknown, try \"ip help\".", 1