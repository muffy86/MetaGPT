#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Configuration models for environment components (MCP/RAG/connectors/skills/tools/access/automation)."""

from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import Field, model_validator

from metagpt.utils.yaml_model import YamlModel


class MCPTransportType(Enum):
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"
    WEBSOCKET = "websocket"


class MCPServerConfig(YamlModel):
    enabled: bool = False
    transport: MCPTransportType = MCPTransportType.STDIO
    command: str = ""
    args: List[str] = Field(default_factory=list)
    url: str = ""
    headers: Dict[str, str] = Field(default_factory=dict)
    env: Dict[str, str] = Field(default_factory=dict)
    timeout: int = 30
    startup_timeout: int = 60
    capabilities: List[str] = Field(default_factory=list)
    read_only: bool = False

    @model_validator(mode="after")
    def check_target(self):
        if not self.enabled:
            return self

        if self.transport == MCPTransportType.STDIO and not self.command:
            raise ValueError("mcp.servers.<name>.command is required when transport is stdio and server is enabled")
        if self.transport != MCPTransportType.STDIO and not self.url:
            raise ValueError("mcp.servers.<name>.url is required for non-stdio transports when server is enabled")
        return self


class MCPConfig(YamlModel):
    enabled: bool = False
    auto_discover: bool = False
    allow_tool_fallback: bool = True
    default_server: Optional[str] = None
    servers: Dict[str, MCPServerConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_default_server(self):
        if self.default_server and self.default_server not in self.servers:
            raise ValueError("mcp.default_server must be one of mcp.servers keys")
        return self


class RAGConfig(YamlModel):
    enabled: bool = False
    retriever: Literal["bm25", "chroma", "faiss", "elasticsearch"] = "bm25"
    ranker: Literal["none", "llm", "object", "colbert", "cohere", "bge"] = "none"
    top_k: int = 5
    chunk_size: int = 1024
    chunk_overlap: int = 128
    persist_path: str = ".rag_data"
    collection_name: str = "metagpt"
    enable_citations: bool = True


class ConnectorAuthType(Enum):
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    OAUTH2 = "oauth2"
    BASIC = "basic"


class ConnectorConfig(YamlModel):
    enabled: bool = False
    provider: str = ""
    endpoint: str = ""
    auth_type: ConnectorAuthType = ConnectorAuthType.NONE
    auth_env: str = ""
    scopes: List[str] = Field(default_factory=list)
    read_only: bool = True
    max_items_per_sync: int = 100
    options: Dict[str, str] = Field(default_factory=dict)


class ConnectorsConfig(YamlModel):
    enabled: bool = False
    default_connector: Optional[str] = None
    items: Dict[str, ConnectorConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_default_connector(self):
        if self.default_connector and self.default_connector not in self.items:
            raise ValueError("connectors.default_connector must be one of connectors.items keys")
        return self


class SkillRuntimeMode(Enum):
    MANUAL = "manual"
    ON_DEMAND = "on_demand"
    ALWAYS_ON = "always_on"


class SkillsConfig(YamlModel):
    enabled: bool = True
    declaration_file: str = "docs/.well-known/skills.yaml"
    entity: str = "Assistant"
    runtime_mode: SkillRuntimeMode = SkillRuntimeMode.ON_DEMAND
    allowlist: List[str] = Field(default_factory=list)
    denylist: List[str] = Field(default_factory=list)
    auto_reload: bool = False


class ToolExecutionMode(Enum):
    ALLOW_ALL = "allow_all"
    ALLOWLISTED = "allowlisted"
    TAGGED = "tagged"


class ToolsConfig(YamlModel):
    enabled: bool = True
    execution_mode: ToolExecutionMode = ToolExecutionMode.ALLOW_ALL
    include_tools: List[str] = Field(default_factory=list)
    exclude_tools: List[str] = Field(default_factory=list)
    include_tags: List[str] = Field(default_factory=list)
    strict_validation: bool = True
    command_timeout: int = 120


class AccessDefaultPolicy(Enum):
    ALLOW = "allow"
    DENY = "deny"


class AccessConfig(YamlModel):
    enabled: bool = False
    default_policy: AccessDefaultPolicy = AccessDefaultPolicy.ALLOW
    allow_network: bool = True
    allow_filesystem_write: bool = True
    allow_shell: bool = False
    allowed_paths: List[str] = Field(default_factory=list)
    denied_paths: List[str] = Field(default_factory=list)
    allowed_tools: List[str] = Field(default_factory=list)
    denied_tools: List[str] = Field(default_factory=list)
    allowed_connectors: List[str] = Field(default_factory=list)
    denied_connectors: List[str] = Field(default_factory=list)


class AutomationTriggerType(Enum):
    MANUAL = "manual"
    SCHEDULE = "schedule"
    EVENT = "event"
    WEBHOOK = "webhook"


class AutomationTriggerConfig(YamlModel):
    enabled: bool = True
    type: AutomationTriggerType = AutomationTriggerType.MANUAL
    schedule: str = ""
    connector: str = ""
    event: str = ""
    condition: str = ""
    payload_template: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_trigger_data(self):
        if not self.enabled:
            return self

        if self.type == AutomationTriggerType.SCHEDULE and not self.schedule:
            raise ValueError("automation.jobs.<name>.trigger.schedule is required for schedule triggers")
        if self.type == AutomationTriggerType.EVENT and (not self.connector or not self.event):
            raise ValueError("automation.jobs.<name>.trigger.connector and trigger.event are required for event triggers")
        return self


class AutomationJobConfig(YamlModel):
    enabled: bool = True
    trigger: AutomationTriggerConfig = Field(default_factory=AutomationTriggerConfig)
    workflow: List[str] = Field(default_factory=list)
    max_retries: int = 2
    retry_backoff_seconds: int = 5
    timeout_seconds: int = 600


class AutomationConfig(YamlModel):
    enabled: bool = False
    dry_run: bool = True
    default_max_concurrency: int = 1
    jobs: Dict[str, AutomationJobConfig] = Field(default_factory=dict)
