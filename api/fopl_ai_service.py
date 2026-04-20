"""
FOPL AI Service
Single responsibility: abstract AI provider calls (Gemini / Groq fallback).
"""
import os
import requests as http
from flask import current_app


def call_ai(prompt_text, system_prompt=None, timeout=30):
    """Try Gemini first, fall back to Groq. Returns the AI text or raises."""
    # ── Try Gemini ───────────────────────────────────────────
    gemini_key = current_app.config.get('GEMINI_API_KEY')
    gemini_server = current_app.config.get('GEMINI_SERVER')
    if gemini_key and gemini_server:
        payload = {'contents': [{'parts': [{'text': prompt_text}]}]}
        if system_prompt:
            payload['system_instruction'] = {'parts': [{'text': system_prompt}]}
        resp = http.post(
            f'{gemini_server}?key={gemini_key}',
            headers={'Content-Type': 'application/json'},
            json=payload, timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data['candidates'][0]['content']['parts'][0]['text']

    # ── Try Groq ─────────────────────────────────────────────
    groq_key = current_app.config.get('GROQ_API_KEY') or os.getenv('GROQ_API_KEY')
    groq_server = current_app.config.get('GROQ_SERVER') or 'https://api.groq.com/openai/v1/chat/completions'
    if groq_key:
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt_text})
        resp = http.post(
            groq_server,
            headers={'Authorization': f'Bearer {groq_key}', 'Content-Type': 'application/json'},
            json={'model': 'llama-3.3-70b-versatile', 'messages': messages, 'temperature': 0.7, 'max_tokens': 1024},
            timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data['choices'][0]['message']['content']

    raise RuntimeError('No AI provider configured. Set GEMINI_API_KEY or GROQ_API_KEY in your .env file.')


def call_ai_chat(system_prompt, history_messages, user_msg, timeout=60):
    """Multi-turn chat: try Gemini then Groq. Returns the AI reply text or raises."""
    # ── Try Gemini ───────────────────────────────────────────
    gemini_key = current_app.config.get('GEMINI_API_KEY')
    gemini_server = current_app.config.get('GEMINI_SERVER')
    if gemini_key and gemini_server:
        gemini_contents = [
            {'role': 'user', 'parts': [{'text': 'You are the FOPL bookstore assistant. Follow the system instructions given to you.'}]},
            {'role': 'model', 'parts': [{'text': "Understood! I'm the FOPL Bookstore Assistant. How can I help you find your next great read today?"}]},
        ]
        for msg in history_messages[-20:]:
            role = 'user' if msg.get('role') == 'user' else 'model'
            text = (msg.get('content') or '').strip()
            if text:
                gemini_contents.append({'role': role, 'parts': [{'text': text}]})
        gemini_contents.append({'role': 'user', 'parts': [{'text': user_msg}]})

        payload = {
            'system_instruction': {'parts': [{'text': system_prompt}]},
            'contents': gemini_contents,
            'generationConfig': {'temperature': 0.7, 'maxOutputTokens': 1024},
        }
        resp = http.post(
            f'{gemini_server}?key={gemini_key}',
            headers={'Content-Type': 'application/json'},
            json=payload, timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data['candidates'][0]['content']['parts'][0]['text']

    # ── Try Groq ─────────────────────────────────────────────
    groq_key = current_app.config.get('GROQ_API_KEY') or os.getenv('GROQ_API_KEY')
    groq_server = current_app.config.get('GROQ_SERVER') or 'https://api.groq.com/openai/v1/chat/completions'
    if groq_key:
        messages = [{'role': 'system', 'content': system_prompt}]
        for msg in history_messages[-20:]:
            role = msg.get('role', 'user')
            text = (msg.get('content') or '').strip()
            if text:
                messages.append({'role': role, 'content': text})
        messages.append({'role': 'user', 'content': user_msg})

        resp = http.post(
            groq_server,
            headers={'Authorization': f'Bearer {groq_key}', 'Content-Type': 'application/json'},
            json={'model': 'llama-3.3-70b-versatile', 'messages': messages, 'temperature': 0.7, 'max_tokens': 1024},
            timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data['choices'][0]['message']['content']

    raise RuntimeError('No AI provider configured. Set GEMINI_API_KEY or GROQ_API_KEY in your .env file.')


def call_ai_vision(prompt_text, image_base64, mime_type='image/jpeg', timeout=30):
    """Send an image + prompt to Gemini Vision, falling back to Groq vision. Returns text or raises."""
    # ── Try Gemini Vision ────────────────────────────────────────────────────
    gemini_key = current_app.config.get('GEMINI_API_KEY')
    gemini_server = current_app.config.get('GEMINI_SERVER')
    if gemini_key and gemini_server:
        payload = {
            'contents': [{
                'parts': [
                    {'text': prompt_text},
                    {'inline_data': {'mime_type': mime_type, 'data': image_base64}}
                ]
            }],
            'generationConfig': {'temperature': 0.4, 'maxOutputTokens': 512}
        }
        resp = http.post(
            f'{gemini_server}?key={gemini_key}',
            headers={'Content-Type': 'application/json'},
            json=payload, timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data['candidates'][0]['content']['parts'][0]['text']
        current_app.logger.warning(f'Gemini Vision failed ({resp.status_code}), trying Groq vision...')

    # ── Try Groq Vision (Llama 4 Scout) ─────────────────────────────────────
    groq_key = current_app.config.get('GROQ_API_KEY') or os.getenv('GROQ_API_KEY')
    if groq_key:
        data_url = f'data:{mime_type};base64,{image_base64}'
        payload = {
            'model': 'meta-llama/llama-4-scout-17b-16e-instruct',
            'messages': [{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': prompt_text},
                    {'type': 'image_url', 'image_url': {'url': data_url}}
                ]
            }],
            'temperature': 0.4,
            'max_tokens': 512,
        }
        resp = http.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {groq_key}', 'Content-Type': 'application/json'},
            json=payload, timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data['choices'][0]['message']['content']
        current_app.logger.warning(f'Groq Vision failed ({resp.status_code}): {resp.text[:200]}')

    raise RuntimeError('No vision AI provider available. Set GEMINI_API_KEY or GROQ_API_KEY.')
