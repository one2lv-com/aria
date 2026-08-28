#!/usr/bin/env python3
"""
ARIA Android App - Main Kivy Entry Point
"""
import os
import sys
from pathlib import Path
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import platform
import threading

# Import agent modules
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from agent import Agent

# Android specific imports
if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([
        Permission.RECORD_AUDIO,
        Permission.INTERNET,
        Permission.WRITE_EXTERNAL_STORAGE,
        Permission.READ_EXTERNAL_STORAGE
    ])


class ChatInterface(BoxLayout):
    def __init__(self, agent, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.agent = agent
        self.processing = False

        # Chat history display
        self.chat_scroll = ScrollView(size_hint=(1, 0.8))
        self.chat_label = Label(
            text='[b][color=00ff00]ARIA Online[/color][/b]\n\nHow can I help you?',
            markup=True,
            size_hint_y=None,
            text_size=(Window.width * 0.95, None),
            halign='left',
            valign='top',
            padding=(10, 10)
        )
        self.chat_label.bind(texture_size=self._update_chat_height)
        self.chat_scroll.add_widget(self.chat_label)
        self.add_widget(self.chat_scroll)

        # Input area
        input_layout = BoxLayout(size_hint=(1, 0.15), spacing=5, padding=5)

        self.input_field = TextInput(
            hint_text='Type your message...',
            multiline=False,
            size_hint=(0.75, 1)
        )
        self.input_field.bind(on_text_validate=self.send_message)
        input_layout.add_widget(self.input_field)

        # Send button
        send_btn = Button(text='Send', size_hint=(0.15, 1))
        send_btn.bind(on_press=self.send_message)
        input_layout.add_widget(send_btn)

        # Voice button (if supported)
        voice_btn = Button(text='🎤', size_hint=(0.1, 1))
        voice_btn.bind(on_press=self.voice_input)
        input_layout.add_widget(voice_btn)

        self.add_widget(input_layout)

        # Control buttons
        control_layout = BoxLayout(size_hint=(1, 0.05), spacing=5, padding=2)

        clear_btn = Button(text='Clear', size_hint=(0.25, 1))
        clear_btn.bind(on_press=self.clear_chat)
        control_layout.add_widget(clear_btn)

        model_btn = Button(text='Model: Kimi', size_hint=(0.25, 1))
        model_btn.bind(on_press=self.toggle_model)
        control_layout.add_widget(model_btn)
        self.model_btn = model_btn

        self.add_widget(control_layout)

    def _update_chat_height(self, instance, value):
        self.chat_label.height = value[1]

    def append_message(self, role, text):
        color = '00ffff' if role == 'user' else '00ff00'
        prefix = 'You' if role == 'user' else 'ARIA'
        current = self.chat_label.text
        self.chat_label.text = f"{current}\n\n[b][color={color}]{prefix}:[/color][/b] {text}"

    def send_message(self, instance=None):
        if self.processing:
            return

        user_input = self.input_field.text.strip()
        if not user_input:
            return

        self.input_field.text = ''
        self.append_message('user', user_input)

        # Process in background thread
        self.processing = True
        thread = threading.Thread(target=self._process_message, args=(user_input,))
        thread.daemon = True
        thread.start()

    def _process_message(self, user_input):
        try:
            # Handle commands
            if user_input.lower() in ('exit', 'quit', 'bye'):
                Clock.schedule_once(lambda dt: self.append_message('agent', 'Goodbye! Close the app to exit.'), 0)
                self.processing = False
                return

            elif user_input.lower() == '/clear':
                Clock.schedule_once(lambda dt: self.clear_chat(), 0)
                self.agent.history.clear()
                self.processing = False
                return

            elif user_input.lower().startswith('/model '):
                model = user_input.split(None, 1)[1].strip()
                self.agent.model = model
                Clock.schedule_once(lambda dt: self.append_message('agent', f'Model switched to: {model}'), 0)
                Clock.schedule_once(lambda dt: setattr(self.model_btn, 'text', f'Model: {model.title()}'), 0)
                self.processing = False
                return

            # Regular chat
            response = self.agent.run_once(user_input)
            Clock.schedule_once(lambda dt: self.append_message('agent', response), 0)

        except Exception as e:
            Clock.schedule_once(lambda dt: self.append_message('agent', f'Error: {str(e)}'), 0)
        finally:
            self.processing = False

    def voice_input(self, instance):
        if self.processing:
            return
        self.append_message('agent', 'Voice input: Feature coming soon on Android!')

    def clear_chat(self, instance=None):
        self.chat_label.text = '[b][color=00ff00]ARIA[/color][/b]\n\nChat cleared. How can I help you?'

    def toggle_model(self, instance):
        models = ['kimi', 'flash', 'step']
        current = self.agent.model
        next_idx = (models.index(current) + 1) % len(models)
        new_model = models[next_idx]
        self.agent.model = new_model
        instance.text = f'Model: {new_model.title()}'


class ARIAApp(App):
    def build(self):
        # Initialize agent
        api_key = os.environ.get('NVIDIA_API_KEY', '')
        if not api_key:
            # Try to load from config file
            config_file = BASE_DIR / 'config.txt'
            if config_file.exists():
                api_key = config_file.read_text().strip()
                os.environ['NVIDIA_API_KEY'] = api_key

        self.agent = Agent(model='kimi', voice=False)
        self.title = 'ARIA - AI Agent'
        return ChatInterface(self.agent)


if __name__ == '__main__':
    ARIAApp().run()
