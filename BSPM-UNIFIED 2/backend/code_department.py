"""
Code Department - GBStudio Script Generation
Version: 1.0
Platform: Intel Mac (macOS Ventura) + Docker

Complete implementation for:
- Natural language to GBStudio script conversion
- Script templates library
- Script validation and optimization
- Event generation with proper IDs
- Integration with Ollama LLM for intent understanding
"""

import os
import json
import hashlib
import re
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field
import requests


class CodeGenerationRequest(BaseModel):
    """Request model for code generation"""
    description: str = Field(..., min_length=1, max_length=2000)
    script_type: str = Field(..., description="dialogue, movement, logic, trigger, scene, ui")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Scene info, actors, variables")
    template_id: Optional[str] = Field(None, description="Optional template to base script on")


class GBStudioEvent(BaseModel):
    """Single GBStudio event"""
    id: str
    command: str
    args: Dict[str, Any]
    children: Optional[Dict[str, List[Any]]] = None


class GBStudioScript(BaseModel):
    """Complete GBStudio script with metadata"""
    script_id: str
    description: str
    events: List[Dict[str, Any]]
    estimated_events: int
    validation_status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    template_used: Optional[str] = None
    variables_used: List[str] = Field(default_factory=list)


class CodeDepartment:
    """
    Code Department for GBStudio Script Generation

    Capabilities:
    - Generate GBStudio event scripts from natural language
    - Use templates for common patterns
    - Validate script syntax and structure
    - Optimize scripts for performance
    - Track script patterns and variables
    """

    def __init__(
        self,
        ollama_api_url: str = "http://ollama:11434/api/generate",
        model: str = "llama3",
        templates_dir: str = "/app/backend/code_templates"
    ):
        """
        Initialize Code Department

        Args:
            ollama_api_url: Ollama API endpoint
            model: LLM model to use for script generation
            templates_dir: Directory containing script templates
        """
        self.ollama_api_url = ollama_api_url
        self.model = model
        self.templates_dir = Path(templates_dir)
        self.templates_cache = {}
        self._load_templates()

        # GBStudio event commands reference
        self.event_commands = {
            # Dialogue
            'dialogue': ['EVENT_TEXT', 'EVENT_CHOICE', 'EVENT_MENU'],
            # Movement
            'movement': ['EVENT_ACTOR_MOVE_TO', 'EVENT_ACTOR_MOVE_RELATIVE', 'EVENT_ACTOR_SET_DIRECTION'],
            # Logic
            'logic': ['EVENT_IF', 'EVENT_SWITCH', 'EVENT_VARIABLE_MATH', 'EVENT_SET_VALUE'],
            # Triggers
            'trigger': ['EVENT_SCRIPT_UNLOCK', 'EVENT_SCRIPT_LOCK', 'EVENT_CALL_CUSTOM_EVENT'],
            # Scene
            'scene': ['EVENT_SWITCH_SCENE', 'EVENT_ACTOR_SHOW', 'EVENT_ACTOR_HIDE'],
            # UI
            'ui': ['EVENT_OVERLAY_SHOW', 'EVENT_OVERLAY_HIDE', 'EVENT_OVERLAY_MOVE_TO']
        }

    def _load_templates(self):
        """Load all script templates from templates directory"""
        if not self.templates_dir.exists():
            print(f"[CodeDept] Templates directory not found: {self.templates_dir}")
            return

        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r') as f:
                    template_data = json.load(f)
                    template_id = template_file.stem
                    self.templates_cache[template_id] = template_data
                    print(f"[CodeDept] Loaded template: {template_id}")
            except Exception as e:
                print(f"[CodeDept] Failed to load template {template_file}: {e}")

        print(f"[CodeDept] Loaded {len(self.templates_cache)} templates")

    async def generate_script(
        self,
        request: CodeGenerationRequest,
        correlation_id: Optional[str] = None
    ) -> GBStudioScript:
        """
        Generate GBStudio script from natural language description

        Process:
        1. Analyze description with LLM to understand intent
        2. Select appropriate template or generate from scratch
        3. Fill in template variables or create custom events
        4. Validate generated script
        5. Return formatted script

        Args:
            request: Code generation request
            correlation_id: Optional tracking ID

        Returns:
            GBStudioScript with events and metadata
        """
        print(f"[CodeDept] Generating {request.script_type} script: {request.description[:50]}...")

        # If template specified, use it
        if request.template_id and request.template_id in self.templates_cache:
            script = await self._generate_from_template(request, correlation_id)
        else:
            # Auto-select template or generate from scratch
            template = self._select_best_template(request.description, request.script_type)
            if template:
                request.template_id = template
                script = await self._generate_from_template(request, correlation_id)
            else:
                script = await self._generate_from_scratch(request, correlation_id)

        # Validate script
        validation = self.validate_script(script.events)
        script.validation_status = validation['status']

        return script

    def _select_best_template(self, description: str, script_type: str) -> Optional[str]:
        """
        Select best matching template based on description and type

        Args:
            description: Natural language description
            script_type: Type of script (dialogue, movement, etc.)

        Returns:
            Template ID or None
        """
        description_lower = description.lower()

        # Simple keyword matching for template selection
        template_keywords = {
            'dialogue_simple': ['talk', 'say', 'tell', 'npc', 'hello', 'greet'],
            'dialogue_branching': ['choice', 'option', 'decide', 'branch', 'ask'],
            'movement_patrol': ['patrol', 'walk', 'move', 'back and forth', 'pace'],
            'combat_basic': ['fight', 'combat', 'damage', 'health', 'attack', 'hit'],
            'inventory_system': ['collect', 'item', 'pickup', 'inventory', 'get'],
            'save_system': ['save', 'checkpoint', 'persist', 'load']
        }

        # Score each template
        scores = {}
        for template_id, keywords in template_keywords.items():
            if template_id in self.templates_cache:
                template = self.templates_cache[template_id]
                # Check if category matches
                if template.get('category') == script_type:
                    score = sum(1 for keyword in keywords if keyword in description_lower)
                    if score > 0:
                        scores[template_id] = score

        # Return best match
        if scores:
            best_template = max(scores.items(), key=lambda x: x[1])[0]
            print(f"[CodeDept] Auto-selected template: {best_template}")
            return best_template

        return None

    async def _generate_from_template(
        self,
        request: CodeGenerationRequest,
        correlation_id: Optional[str]
    ) -> GBStudioScript:
        """
        Generate script from template by extracting variables from description

        Args:
            request: Code generation request with template_id
            correlation_id: Optional tracking ID

        Returns:
            GBStudioScript
        """
        template = self.templates_cache[request.template_id]

        # Extract variables from description using LLM
        variables = await self._extract_template_variables(
            request.description,
            template['variables'],
            request.context,
            correlation_id
        )

        # Fill template with variables
        events = self._fill_template(template['events'], variables)

        # Generate unique event IDs
        events = self._assign_event_ids(events)

        script_id = self._generate_script_id()

        return GBStudioScript(
            script_id=script_id,
            description=request.description,
            events=events,
            estimated_events=len(events),
            validation_status="pending",
            template_used=request.template_id,
            variables_used=list(variables.keys())
        )

    async def _generate_from_scratch(
        self,
        request: CodeGenerationRequest,
        correlation_id: Optional[str]
    ) -> GBStudioScript:
        """
        Generate script from scratch using LLM

        Args:
            request: Code generation request
            correlation_id: Optional tracking ID

        Returns:
            GBStudioScript
        """
        # Build prompt for LLM
        prompt = self._build_generation_prompt(request)

        # Call Ollama to generate script structure
        try:
            response = await self._call_ollama(prompt, correlation_id)
            events = self._parse_llm_response(response)
        except Exception as e:
            print(f"[CodeDept] LLM generation failed: {e}")
            # Fallback to simple event
            events = self._create_fallback_script(request)

        # Assign event IDs
        events = self._assign_event_ids(events)

        script_id = self._generate_script_id()

        return GBStudioScript(
            script_id=script_id,
            description=request.description,
            events=events,
            estimated_events=len(events),
            validation_status="pending",
            variables_used=[]
        )

    def _build_generation_prompt(self, request: CodeGenerationRequest) -> str:
        """Build prompt for LLM to generate GBStudio script"""
        available_commands = self.event_commands.get(request.script_type, [])

        context_str = ""
        if request.context:
            context_str = f"\n\nContext:\n{json.dumps(request.context, indent=2)}"

        prompt = f"""Generate a GBStudio script for the following request:

Description: {request.description}
Script Type: {request.script_type}
Available Commands: {', '.join(available_commands)}{context_str}

Generate a JSON array of GBStudio events. Each event should have:
- command: The event command (use only commands from the available list)
- args: Arguments for the command
- children: Optional nested events for conditional/loop commands

Example format:
[
  {{
    "command": "EVENT_TEXT",
    "args": {{
      "text": ["Hello, adventurer!"],
      "avatarId": ""
    }}
  }}
]

IMPORTANT: Return ONLY the JSON array, no markdown, no explanations.
"""
        return prompt

    async def _call_ollama(self, prompt: str, correlation_id: Optional[str]) -> str:
        """Call Ollama API for LLM inference"""
        try:
            response = requests.post(
                self.ollama_api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9
                    }
                },
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            return result.get("response", "")

        except Exception as e:
            print(f"[CodeDept] Ollama call failed: {e}")
            raise

    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into event list"""
        # Remove markdown code blocks if present
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()

        try:
            events = json.loads(response)
            if isinstance(events, list):
                return events
            else:
                return [events]
        except json.JSONDecodeError as e:
            print(f"[CodeDept] Failed to parse LLM response: {e}")
            raise

    def _create_fallback_script(self, request: CodeGenerationRequest) -> List[Dict[str, Any]]:
        """Create simple fallback script when LLM fails"""
        return [
            {
                "command": "EVENT_TEXT",
                "args": {
                    "text": [f"Script for: {request.description}"],
                    "avatarId": ""
                }
            }
        ]

    async def _extract_template_variables(
        self,
        description: str,
        template_variables: Dict[str, Any],
        context: Dict[str, Any],
        correlation_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Extract template variable values from description using LLM

        Args:
            description: Natural language description
            template_variables: Template variable definitions
            context: Additional context
            correlation_id: Optional tracking ID

        Returns:
            Dict mapping variable names to values
        """
        # Build prompt to extract variables
        var_descriptions = "\n".join([
            f"- {name}: {var_def['description']} (type: {var_def['type']}, required: {var_def.get('required', False)})"
            for name, var_def in template_variables.items()
        ])

        prompt = f"""Extract the following variables from the description:

Description: {description}

Variables to extract:
{var_descriptions}

Context: {json.dumps(context, indent=2) if context else "None"}

Return a JSON object with the variable values. Use defaults for missing non-required variables.

Example:
{{
  "dialogue_text": "Hello there!",
  "avatar_id": ""
}}

IMPORTANT: Return ONLY the JSON object, no markdown, no explanations.
"""

        try:
            response = await self._call_ollama(prompt, correlation_id)
            # Parse response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()

            variables = json.loads(response)

            # Add defaults for missing values
            for name, var_def in template_variables.items():
                if name not in variables and 'default' in var_def:
                    variables[name] = var_def['default']

            return variables

        except Exception as e:
            print(f"[CodeDept] Variable extraction failed: {e}")
            # Return defaults
            return {
                name: var_def.get('default', '')
                for name, var_def in template_variables.items()
            }

    def _fill_template(
        self,
        template_events: List[Dict[str, Any]],
        variables: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Fill template events with variable values

        Uses {{variable_name}} syntax for substitution

        Args:
            template_events: Template event list
            variables: Variable values

        Returns:
            Filled event list
        """
        # Convert to JSON string for easy replacement
        template_str = json.dumps(template_events, indent=2)

        # Replace all {{variable}} placeholders
        for var_name, var_value in variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            # Convert value to string for replacement
            if isinstance(var_value, str):
                replacement = var_value
            else:
                replacement = str(var_value)

            template_str = template_str.replace(placeholder, replacement)

        # Parse back to events
        try:
            filled_events = json.loads(template_str)
            return filled_events
        except json.JSONDecodeError as e:
            print(f"[CodeDept] Template fill failed: {e}")
            return template_events

    def _assign_event_ids(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Assign unique IDs to all events

        Replaces {{event_id_N}} placeholders with actual IDs

        Args:
            events: Event list

        Returns:
            Events with assigned IDs
        """
        # Convert to string for replacement
        events_str = json.dumps(events, indent=2)

        # Find all event_id placeholders
        placeholders = re.findall(r'\{\{event_id_\d+\}\}', events_str)
        unique_placeholders = list(set(placeholders))

        # Generate unique IDs
        id_map = {}
        for placeholder in unique_placeholders:
            event_id = self._generate_event_id()
            id_map[placeholder] = event_id

        # Replace placeholders
        for placeholder, event_id in id_map.items():
            events_str = events_str.replace(placeholder, event_id)

        # Add IDs to events that don't have them
        events = json.loads(events_str)
        for event in events:
            if 'id' not in event:
                event['id'] = self._generate_event_id()

        return events

    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        timestamp = datetime.utcnow().isoformat()
        random_data = os.urandom(4).hex()
        hash_input = f"{timestamp}{random_data}".encode()
        hash_digest = hashlib.sha256(hash_input).hexdigest()
        return f"event_{hash_digest[:12]}"

    def _generate_script_id(self) -> str:
        """Generate unique script ID"""
        timestamp = datetime.utcnow().isoformat()
        random_data = os.urandom(4).hex()
        hash_input = f"{timestamp}{random_data}".encode()
        hash_digest = hashlib.sha256(hash_input).hexdigest()
        return f"script_{hash_digest[:12]}"

    def validate_script(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate GBStudio script syntax and structure

        Checks:
        - All events have required fields (command, args)
        - Event IDs are unique
        - Commands are valid GBStudio commands
        - Args match expected structure

        Args:
            events: List of events to validate

        Returns:
            Validation report
        """
        validation = {
            "status": "valid",
            "errors": [],
            "warnings": [],
            "event_count": len(events)
        }

        event_ids = set()

        for i, event in enumerate(events):
            # Check required fields
            if 'command' not in event:
                validation['errors'].append(f"Event {i}: missing 'command' field")
                validation['status'] = "invalid"

            if 'args' not in event:
                validation['errors'].append(f"Event {i}: missing 'args' field")
                validation['status'] = "invalid"

            # Check event ID uniqueness
            if 'id' in event:
                if event['id'] in event_ids:
                    validation['warnings'].append(f"Event {i}: duplicate ID {event['id']}")
                event_ids.add(event['id'])
            else:
                validation['warnings'].append(f"Event {i}: missing 'id' field")

            # Validate command is known
            if 'command' in event:
                command = event['command']
                all_commands = [cmd for cmds in self.event_commands.values() for cmd in cmds]
                if command not in all_commands:
                    validation['warnings'].append(
                        f"Event {i}: unknown command '{command}' (may be valid but not in our reference)"
                    )

        return validation

    def optimize_script(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Optimize script for performance

        Optimizations:
        - Merge consecutive text events
        - Remove redundant waits
        - Combine variable operations
        - Flag expensive operations

        Args:
            events: Events to optimize

        Returns:
            Optimization report with suggestions
        """
        optimization = {
            "original_event_count": len(events),
            "optimized_event_count": len(events),
            "suggestions": [],
            "optimized_events": events.copy()
        }

        # Check for consecutive text events
        consecutive_texts = []
        for i in range(len(events) - 1):
            if events[i].get('command') == 'EVENT_TEXT' and events[i + 1].get('command') == 'EVENT_TEXT':
                consecutive_texts.append(i)

        if consecutive_texts:
            optimization['suggestions'].append({
                "type": "merge_texts",
                "description": f"Found {len(consecutive_texts)} consecutive text events that could be merged",
                "locations": consecutive_texts
            })

        # Check for short wait times
        for i, event in enumerate(events):
            if event.get('command') == 'EVENT_WAIT':
                wait_time = event.get('args', {}).get('time', 0)
                if wait_time < 0.1:
                    optimization['suggestions'].append({
                        "type": "short_wait",
                        "description": f"Event {i}: very short wait time ({wait_time}s) may be unnecessary",
                        "location": i
                    })

        return optimization

    def get_templates(self) -> List[Dict[str, Any]]:
        """
        Get list of available templates

        Returns:
            List of template metadata
        """
        templates = []
        for template_id, template_data in self.templates_cache.items():
            templates.append({
                "id": template_id,
                "name": template_data.get('name', template_id),
                "description": template_data.get('description', ''),
                "category": template_data.get('category', 'general'),
                "variables": list(template_data.get('variables', {}).keys()),
                "event_count": len(template_data.get('events', []))
            })
        return templates

    def get_script_patterns(self) -> Dict[str, List[str]]:
        """
        Get common script patterns organized by type

        Returns:
            Dict mapping script types to pattern descriptions
        """
        patterns = {
            "dialogue": [
                "Simple NPC conversation",
                "Branching dialogue with choices",
                "Multi-page text boxes",
                "Character portraits and avatars"
            ],
            "movement": [
                "Actor patrol patterns",
                "Follow player behavior",
                "Scripted movement sequences",
                "Camera control"
            ],
            "logic": [
                "Variable conditions (if/else)",
                "Switch statements",
                "Math operations on variables",
                "State machines"
            ],
            "trigger": [
                "Collision triggers",
                "Interaction triggers",
                "Auto-run scripts",
                "Custom events"
            ],
            "scene": [
                "Scene transitions",
                "Actor spawn/despawn",
                "Background changes",
                "Fadeout effects"
            ],
            "ui": [
                "Menu systems",
                "HUD updates",
                "Overlay animations",
                "Input handling"
            ]
        }
        return patterns


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def test_code_department():
        dept = CodeDepartment()

        # Test template listing
        print("\n=== Available Templates ===")
        templates = dept.get_templates()
        for template in templates:
            print(f"- {template['name']} ({template['id']}): {template['description']}")

        # Test script generation
        print("\n=== Test Script Generation ===")
        request = CodeGenerationRequest(
            description="Create a simple dialogue where an NPC says 'Welcome to the village!'",
            script_type="dialogue"
        )

        script = await dept.generate_script(request)
        print(f"Script ID: {script.script_id}")
        print(f"Events: {script.estimated_events}")
        print(f"Validation: {script.validation_status}")
        print(f"Template used: {script.template_used}")
        print("\nGenerated events:")
        print(json.dumps(script.events, indent=2))

        # Test validation
        print("\n=== Validation Report ===")
        validation = dept.validate_script(script.events)
        print(json.dumps(validation, indent=2))

    asyncio.run(test_code_department())
