#!/usr/bin/env python3
"""
ARIA — Autonomous Reasoning Intelligence Agent
Terminal agent with voice, memory, tools, skill learning, swarm, and build coordination.
"""
import os
import sys
import json
import re
import argparse
from datetime import datetime
from pathlib import Path

# ── path setup ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# ── rich UI ──────────────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.live import Live
    from rich.text import Text
    from rich.prompt import Prompt
    RICH = True
except ImportError:
    RICH = False

# ── tools ────────────────────────────────────────────────────────────────────
from tools.llm_tool import LLMTool
from tools.memory_tool import MemoryTool
from tools.shell_tool import ShellTool
from tools.file_tool import FileTool
from tools.voice_tool import VoiceTool
from tools.learn_tool import LearnTool
from tools.swarm_tool import SwarmTool
from tools.vision_tool import VisionTool
from tools.maton_tool import MatonTool, maton_tool_dispatch
from tools.build_lobby import (
    BuildLobby, Agent as LobbyAgent, AgentRole, LobbyMessage, MessageType,
    get_lobby, join_lobby, leave_lobby, log_build_phase, 
    log_error, log_warning, chat
)
from swarm.coordinator import SwarmCoordinator

console = Console() if RICH else None

# Global lobby instance for this ARIA session
ARIA_LOBBY: BuildLobby = None
ARIA_LOBBY_AGENT_ID: str = None


# ── helpers ───────────────────────────────────────────────────────────────────
def print_info(msg: str):
    if RICH:
        console.print(f"[dim]{msg}[/dim]")
    else:
        print(msg)

def print_user(msg: str):
    if RICH:
        console.print(f"\n[bold cyan]You:[/bold cyan] {msg}")
    else:
        print(f"\nYou: {msg}")

def print_agent(msg: str, stream: bool = False):
    if RICH:
        console.print(Panel(Markdown(msg), title="[bold green]ARIA[/bold green]", border_style="green"))
    else:
        print(f"\nARIA: {msg}\n")

def print_tool(tool: str, action: str, result: str):
    if RICH:
        console.print(f"[yellow]  [{tool}][/yellow] {action} → {result[:120]}{'...' if len(result) > 120 else ''}")
    else:
        print(f"  [{tool}] {action}")

def load_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


# ── system prompt builder ─────────────────────────────────────────────────────
def build_system_prompt(soul: str, memory: str, skills: str, tools_md: str) -> str:
    return f"""You are ARIA, an autonomous terminal AI agent.

=== SOUL ===
{soul}

=== CURRENT MEMORY ===
{memory or "(empty)"}

=== AVAILABLE SKILLS ===
{skills}

=== AVAILABLE TOOLS ===
{tools_md}

=== TOOL CALL FORMAT ===
When you need to use a tool, output a JSON block like this (and NOTHING else on those lines):
```tool
{"tool": "shell", "action": "run", "args": {"command": "ls -la"}}
```
Supported tools: shell, file, memory, swarm, learn, voice, vision, lobby
After using a tool you will receive its result and can continue your response.

=== RULES ===
1. Think step by step for complex tasks.
2. Use tools when needed — don't fake results.
3. Update memory with important facts using the memory tool.
4. For parallel/complex tasks use swarm.
5. For image analysis use the vision tool.
6. For build coordination use the lobby tool.
7. If you learn a new skill or tool, register it with the learn tool.
8. Be concise unless the user asks for detail.
9. Today's date: {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""


# ── tool dispatcher ───────────────────────────────────────────────────────────
class ToolDispatcher:
    def __init__(self):
        self.shell = ShellTool()
        self.file = FileTool()
        self.memory = MemoryTool()
        self.swarm_tool = SwarmTool()
        self.learn = LearnTool()
        self.voice = VoiceTool()
        self.vision = VisionTool()
        self.maton = MatonTool()
        self.swarm_coord = SwarmCoordinator()
        
        # Initialize Build Lobby for this session
        global ARIA_LOBBY, ARIA_LOBBY_AGENT_ID
        ARIA_LOBBY = get_lobby()
        ARIA_LOBBY_AGENT_ID = f"aria-{datetime.now().strftime('%H%M%S')}"
        join_lobby(ARIA_LOBBY_AGENT_ID, AgentRole.ORCHESTRATOR, "ARIA Primary", {
            "session": "interactive",
            "pid": os.getpid()
        })

    def dispatch(self, call: dict) -> str:
        tool = call.get("tool", "")
        action = call.get("action", "")
        args = call.get("args", {})

        try:
            if tool == "shell":
                r = self.shell.run(**args)
                out = r.get("stdout") or r.get("error", "")
                err = r.get("stderr", "")
                print_tool("shell", args.get("command", ""), out or err)
                return f"stdout: {out}\nstderr: {err}\ncode: {r.get('code', -1)}"

            elif tool == "file":
                method = getattr(self.file, action, None)
                if not method:
                    return f"Unknown file action: {action}"
                r = method(**args)
                print_tool("file", f"{action} {list(args.values())[:1]}", str(r))
                return json.dumps(r)

            elif tool == "memory":
                method = getattr(self.memory, action, None)
                if not method:
                    return f"Unknown memory action: {action}"
                r = method(**args)
                print_tool("memory", action, str(r)[:80])
                return json.dumps(r)

            elif tool == "swarm":
                if action == "run":
                    goal = args.get("goal", "")
                    print_tool("swarm", f"coordinating: {goal[:60]}", "spawning agents...")
                    r = self.swarm_coord.run(goal)
                    return f"Tasks: {r['tasks']}\n\nFinal answer:\n{r['final']}"
                elif action == "spawn":
                    r = self.swarm_tool.spawn(**args)
                    return json.dumps(r)
                return "Unknown swarm action"

            elif tool == "learn":
                method = getattr(self.learn, action, None)
                if not method:
                    return f"Unknown learn action: {action}"
                r = method(**args)
                print_tool("learn", f"{action}", str(r))
                return json.dumps(r)

            elif tool == "voice":
                method = getattr(self.voice, action, None)
                if not method:
                    return f"Unknown voice action: {action}"
                r = method(**args)
                return json.dumps(r)

            elif tool == "vision":
                method = getattr(self.vision, action, None)
                if not method:
                    return f"Unknown vision action: {action}"
                r = method(**args)
                print_tool("vision", f"{action}", str(r)[:120])
                return json.dumps(r)

            elif tool == "maton":
                return maton_tool_dispatch(action, args)
            elif tool == "lobby":
                return self._dispatch_lobby(action, args)

            return f"Unknown tool: {tool}"

        except Exception as e:
            return f"Tool error: {e}"

    def _dispatch_lobby(self, action: str, args: dict) -> str:
        """Handle Build Lobby tool calls."""
        global ARIA_LOBBY, ARIA_LOBBY_AGENT_ID
        
        if not ARIA_LOBBY:
            return "Lobby not initialized"
        
        try:
            if action == "broadcast":
                content = args.get("content", "")
                msg_type = MessageType(args.get("type", "chat"))
                ARIA_LOBBY.broadcast(ARIA_LOBBY_AGENT_ID, msg_type, content, args.get("metadata"))
                return f"Broadcast sent: {content[:50]}..."
            
            elif action == "direct_message":
                to_agent = args.get("to_agent", "")
                content = args.get("content", "")
                msg_type = MessageType(args.get("type", "chat"))
                ARIA_LOBBY.direct_message(ARIA_LOBBY_AGENT_ID, to_agent, msg_type, content, args.get("metadata"))
                return f"DM sent to {to_agent}: {content[:50]}..."
            
            elif action == "get_messages":
                since = args.get("since")
                for_agent = args.get("for_agent", ARIA_LOBBY_AGENT_ID)
                msgs = ARIA_LOBBY.get_messages(since=since, for_agent=for_agent)
                return json.dumps(msgs)
            
            elif action == "update_state":
                ARIA_LOBBY.update_build_state(**args.get("state", {}))
                return "Build state updated"
            
            elif action == "add_blocker":
                ARIA_LOBBY.add_blocker(args.get("blocker", ""))
                return "Blocker added"
            
            elif action == "remove_blocker":
                ARIA_LOBBY.remove_blocker(args.get("blocker", ""))
                return "Blocker removed"
            
            elif action == "add_patch":
                ARIA_LOBBY.add_patch(args.get("patch", ""))
                return "Patch recorded"
            
            elif action == "add_artifact":
                ARIA_LOBBY.add_artifact(args.get("artifact", ""))
                return "Artifact recorded"
            
            elif action == "heartbeat":
                ARIA_LOBBY.heartbeat(ARIA_LOBBY_AGENT_ID)
                return "Heartbeat sent"
            
            elif action == "get_state":
                return json.dumps(ARIA_LOBBY.get_state(), indent=2)
            
            elif action == "phase_change":
                phase_name = args.get("phase", "")
                details = args.get("details", "")
                log_build_phase(phase_name, details)
                return f"Phase changed to: {phase_name}"
            
            elif action == "join":
                agent_id = args.get("agent_id", f"aria-{datetime.now().strftime('%H%M%S')}")
                role = AgentRole(args.get("role", "watcher"))
                name = args.get("name", "ARIA Agent")
                join_lobby(agent_id, role, name, args.get("metadata"))
                return f"Joined lobby as {agent_id}"
            
            elif action == "leave":
                reason = args.get("reason", "completed")
                leave_lobby(ARIA_LOBBY_AGENT_ID, reason)
                return f"Left lobby: {reason}"
            
            else:
                return f"Unknown lobby action: {action}"
                
        except Exception as e:
            return f"Lobby error: {e}"


# ── main agent class ──────────────────────────────────────────────────────────
class Agent:
    def __init__(self, model: str = "kimi", voice: bool = False):
        self.model = model
        self.voice_enabled = voice
        self.dispatcher = ToolDispatcher()
        self.history = []
        self.llm = LLMTool(model=model)
        
        # Load soul
        self.soul = load_file(BASE_DIR / "soul.md")
        
        # Load skills & tools descriptions
        self.skills_list = self.dispatcher.learn.list_skills().get("skills", [])
        self.tools_list = self.dispatcher.learn.list_tools().get("tools", [])
        
        print_info(f"ARIA initialized (model: {model}, voice: {voice})")
        print_info(f"Skills: {', '.join(self.skills_list) if self.skills_list else 'none'}")
        print_info(f"Tools: {', '.join(self.tools_list)}")

    def _get_tools_markdown(self) -> str:
        """Generate markdown documentation for all available tools."""
        base_tools = """
**shell** — Run shell commands
- `run`: `{"command": "ls -la"}`

**file** — File operations
- `read`: `{"path": "file.txt"}`
- `write`: `{"path": "file.txt", "content": "hello"}`
- `append`: `{"path": "file.txt", "content": "more"}`
- `list`: `{"path": "."}`

**memory** — Persistent memory
- `read`: `{}`
- `write`: `{"content": "fact to remember"}`
- `search`: `{"query": "keyword"}`

**swarm** — Multi-agent coordination
- `run`: `{"goal": "complex task description"}`
- `spawn`: `{"role": "researcher", "task": "find info"}`

**learn** — Skill/tool registry
- `register_skill`: `{"name": "skill_name", "description": "...", "code": "..."}`
- `register_tool`: `{"name": "tool_name", "description": "...", "module": "tools.my_tool"}`
- `list_skills`: `{}`
- `list_tools`: `{}`

**voice** — Voice I/O
- `speak`: `{"text": "hello"}`
- `listen`: `{"duration": 5}`
- `toggle`: `{}`

**vision** — Image analysis (NVIDIA NIM)
- `analyze`: `{"image_url": "https://...", "prompt": "What is in this image?"}`
- `analyze_local`: `{"image_path": "/path/to/image.jpg", "prompt": "Describe this"}`

**lobby** — Build coordination (multi-agent)
- `broadcast`: `{"content": "message", "type": "status|error|warning|chat|phase_change"}`
- `direct_message`: `{"to_agent": "agent-id", "content": "message", "type": "chat"}`
- `get_messages`: `{"since": "ISO-timestamp", "for_agent": "agent-id"}`
- `update_state`: `{"state": {"phase": "building", "progress": 50}}`
- `add_blocker`: `{"blocker": "description"}`
- `remove_blocker`: `{"blocker": "description"}`
- `add_patch`: `{"patch": "description"}`
- `add_artifact`: `{"artifact": "apk:aria-1.0.apk:15.2MB"}`
- `heartbeat`: `{}`
- `get_state`: `{}`
- `phase_change`: `{"phase": "compiling", "details": "Building Kivy"}`
- `join`: `{"agent_id": "worker-1", "role": "builder", "name": "Build Worker"}`
- `leave`: `{"reason": "done"}`


**maton** — Universal App Gateway (Maton.ai)
- `list_connections`: `{"app": "slack"}` (optional filter)
- `create_connection`: `{"app": "slack", "metadata": {}}`
- `get_connection`: `{"connection_id": "..."}`
- `delete_connection`: `{"connection_id": "..."}`
- `call_api`: `{"app": "slack", "endpoint": "/api/conversations.list", "method": "GET", "params": {}, "json_data": {}}`
- `slack_channels`: `{"types": "public_channel", "limit": 20}`
- `slack_post`: `{"channel": "C123", "text": "Hello", "blocks": []}`
- `github_repo`: `{"owner": "user", "repo": "repo"}`
- `github_issues`: `{"owner": "user", "repo": "repo", "state": "open"}`
- `github_create_issue`: `{"owner": "user", "repo": "repo", "title": "Bug", "body": "Details"}`
- `gmail_messages`: `{"query": "is:unread", "max_results": 10}`
- `gmail_send`: `{"to": "email@domain.com", "subject": "Hi", "body": "Message"}`
- `notion_search`: `{"query": "project notes"}`
- `notion_query`: `{"database_id": "...", "filter": {}}`
- `linear_issues`: `{"team_id": "..."}`
- `supabase_query`: `{"table": "users", "select": "*", "filters": {}}`
- `stripe_customers`: `{"limit": 10}`
- `x_tweet`: `{"text": "Hello world"}`
- `discord_message`: `{"channel_id": "...", "content": "Hi"}`
- `create_trigger`: `{"connection_id": "...", "event": "message.posted", "config": {}}`
- `list_triggers`: `{"connection_id": "..."}`

Supported apps: slack, github, gmail, notion, salesforce, jira, linear, supabase, stripe, x, linkedin, discord

"""
        return base_tools

    def _speak(self, text: str):
        if self.voice_enabled:
            self.dispatcher.voice.speak(text=text)

    def run_once(self, user_input: str) -> str:
        # Update memory context
        mem = self.dispatcher.memory.read().get("content", "")
        
        skills_md = "\n".join(f"- {s}" for s in self.skills_list) if self.skills_list else "(none)"
        tools_md = self._get_tools_markdown()
        
        system_prompt = build_system_prompt(self.soul, mem, skills_md, tools_md)
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history (last 10 turns)
        for turn in self.history[-10:]:
            messages.append({"role": "user", "content": turn["user"]})
            messages.append({"role": "assistant", "content": turn["assistant"]})
        
        messages.append({"role": "user", "content": user_input})
        
        # Call LLM
        response = self.llm.chat(messages)
        
        # Check for tool calls
        while "```tool" in response:
            # Extract tool call
            match = re.search(r"```tool\n(\{.*?\})\n```", response, re.DOTALL)
            if not match:
                break
            
            tool_call = json.loads(match.group(1))
            result = self.dispatcher.dispatch(tool_call)
            
            # Replace tool call with result and continue
            response = response[:match.start()] + f"\n[Tool Result]: {result}\n" + response[match.end():]
            
            # Get continuation from LLM
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": "Continue. Use tools if needed, otherwise provide final answer."})
            response = self.llm.chat(messages)
        
        # Update history
        self.history.append({"user": user_input, "assistant": response})
        
        return response

    def chat_loop(self):
        if RICH:
            console.print(Panel("[bold green]ARIA[/bold green] — Autonomous Agent\nType `help` for commands", border_style="green"))
        else:
            print("ARIA — Autonomous Agent. Type 'help' for commands.")
        
        while True:
            try:
                user_input = Prompt.ask("[bold cyan]You[/bold cyan]") if RICH else input("\nYou: ")
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ("exit", "quit"):
                    if ARIA_LOBBY:
                        leave_lobby(ARIA_LOBBY_AGENT_ID, "user_exit")
                    print_info("Goodbye!")
                    break
                
                elif user_input.lower() == "help":
                    help_text = (
                        "**Commands:**\n"
                        "- `exit` / `quit` — exit\n"
                        "- `/model flash` or `/model kimi` — switch model\n"
                        "- `/voice` — toggle voice\n"
                        "- `/swarm <goal>` — run swarm coordinator on a goal\n"
                        "- `/clear` — clear conversation history\n"
                        "- `/skills` — list known skills\n"
                        "- `/tools` — list known tools\n"
                        "- `/memory` — show current memory\n"
                        "- `/lobby` — show build lobby state\n"
                        "- `/vision <url> <prompt>` — analyze image\n"
                        "- Anything else — chat with ARIA"
                    )
                    print_agent(help_text)
                    continue
                
                elif user_input.lower().startswith("/model "):
                    m = user_input.split(None, 1)[1].strip()
                    self.model = m
                    self.llm = LLMTool(model=m)
                    print_info(f"Model set to: {m}")
                    continue
                
                elif user_input.lower() == "/voice":
                    self.voice_enabled = not self.voice_enabled
                    print_info(f"Voice {'enabled' if self.voice_enabled else 'disabled'}")
                    continue
                
                elif user_input.lower() == "/clear":
                    self.history.clear()
                    print_info("Conversation history cleared.")
                    continue
                
                elif user_input.lower() == "/skills":
                    r = self.dispatcher.learn.list_skills()
                    print_agent("**Skills:** " + ", ".join(r["skills"]))
                    continue
                
                elif user_input.lower() == "/tools":
                    r = self.dispatcher.learn.list_tools()
                    print_agent("**Tools:** " + ", ".join(r["tools"]))
                    continue
                
                elif user_input.lower() == "/memory":
                    r = self.dispatcher.memory.read()
                    print_agent(r["content"] or "(empty memory)")
                    continue
                
                elif user_input.lower() == "/lobby":
                    if ARIA_LOBBY:
                        state = ARIA_LOBBY.get_state()
                        print_agent(f"**Build Lobby State:**\n```json\n{json.dumps(state, indent=2)[:3000]}```")
                    else:
                        print_info("Lobby not initialized")
                    continue
                
                elif user_input.lower().startswith("/vision "):
                    parts = user_input.split(None, 2)
                    if len(parts) >= 3:
                        url = parts[1]
                        prompt = parts[2]
                        print_info(f"Analyzing image: {url}")
                        result = self.dispatcher.vision.analyze(image_url=url, prompt=prompt)
                        print_agent(f"**Vision Analysis:**\n{result}")
                    else:
                        print_info("Usage: /vision <image_url> <prompt>")
                    continue

                elif user_input.lower().startswith("/maton "):
                    parts = user_input.split(None, 2)
                    if len(parts) >= 2:
                        action = parts[1]
                        args_str = parts[2] if len(parts) > 2 else "{}"
                        try:
                            import json
                            args = json.loads(args_str)
                        except:
                            args = {}
                        print_info(f"Maton action: {action}")
                        result = maton_tool_dispatch(action, args)
                        print_agent(f"**Maton Result:**\n```json\n{result}\n```")
                    else:
                        print_info("Usage: /maton <action> [json_args]")
                        print_info("Actions: list_connections, create_connection, slack_channels, github_repo, gmail_messages, etc.")
                    continue
                
                elif user_input.lower().startswith("/swarm "):
                    goal = user_input[7:].strip()
                    if RICH:
                        console.print("[dim]Running swarm coordinator...[/dim]")
                    result = self.dispatcher.swarm_coord.run(goal)
                    output = f"**Goal:** {result['goal']}\n\n**Sub-tasks:**\n"
                    output += "\n".join(f"- {t}" for t in result["tasks"])
                    output += f"\n\n**Final Answer:**\n{result['final']}"
                    print_agent(output)
                    self._speak(result["final"])
                    continue
                
                # Regular chat
                response = self.run_once(user_input)
                print_agent(response)
                self._speak(response)
                
            except KeyboardInterrupt:
                print("\n[Interrupted]")
                break
            except EOFError:
                break


# ── entry point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="ARIA — Autonomous Terminal Agent")
    parser.add_argument("--model", default="kimi", choices=["flash", "kimi", "step"],
                        help="LLM model (flash=step-3.5, kimi=kimi-k2)")
    parser.add_argument("--voice", action="store_true", help="Enable voice I/O")
    parser.add_argument("--key", help="NVIDIA API key (or set NVIDIA_API_KEY env var)")
    parser.add_argument("--once", help="Run a single prompt non-interactively and exit")
    args = parser.parse_args()

    if args.key:
        os.environ["NVIDIA_API_KEY"] = args.key

    if not os.environ.get("NVIDIA_API_KEY"):
        print("WARNING: NVIDIA_API_KEY not set. Set it with --key or export NVIDIA_API_KEY=<key>")
        print("Get a free key at: https://build.nvidia.com")

    agent = Agent(model=args.model, voice=args.voice)

    if args.once:
        response = agent.run_once(args.once)
        print(response)
    else:
        agent.chat_loop()


if __name__ == "__main__":
    main()
