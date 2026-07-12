#!/usr/bin/env python3
"""
Viseme Generator - конвертирует текст в последовательность визем для lip sync
Поддерживает русский и английский языки
"""

import re
from typing import List, Tuple

# ============== VISEME MAPPINGS ==============

# Русские фонемы -> виземы
RUSSIAN_MAP = {
    # Гласные
    'а': 'A', 'я': 'A',
    'э': 'E', 'е': 'E', 'ё': 'E',
    'и': 'I', 'й': 'I', 'ы': 'I',
    'о': 'O',
    'у': 'U', 'ю': 'U',
    
    # Губные согласные (губы смыкаются)
    'м': 'M', 'б': 'M', 'п': 'M',
    
    # Губно-зубные (нижняя губа к зубам)
    'ф': 'F', 'в': 'F',
    
    # Переднеязычные (язык к зубам/альвеолам)
    'т': 'L', 'д': 'L', 'н': 'L', 'л': 'L',
    
    # Свистящие (зубы сближены)
    'с': 'S', 'з': 'S', 'ц': 'S',
    
    # Шипящие (губы округлены вперед)
    'ш': 'SH', 'ж': 'SH', 'ч': 'SH', 'щ': 'SH',
    
    # Заднеязычные (минимальное движение губ)
    'к': 'REST', 'г': 'REST', 'х': 'REST',
    
    # Р (слегка округлен)
    'р': 'R',
}

# Английские фонемы -> виземы
ENGLISH_MAP = {
    # Vowels
    'a': 'A', 'ah': 'A', 'aa': 'A',
    'e': 'E', 'eh': 'E', 'ae': 'E',
    'i': 'I', 'ih': 'I', 'iy': 'I', 'y': 'I',
    'o': 'O', 'oh': 'O', 'ow': 'O', 'aw': 'O',
    'u': 'U', 'uh': 'U', 'uw': 'U', 'oo': 'U',
    
    # Bilabial (lips together)
    'm': 'M', 'b': 'M', 'p': 'M',
    
    # Labiodental (teeth on lip)
    'f': 'F', 'v': 'F',
    
    # Dental/Alveolar
    't': 'L', 'd': 'L', 'n': 'L', 'l': 'L',
    
    # Sibilants
    's': 'S', 'z': 'S',
    
    # Postalveolar
    'sh': 'SH', 'ch': 'SH', 'j': 'SH', 'zh': 'SH',
    
    # Dental fricative
    'th': 'TH',
    
    # R sound
    'r': 'R',
    
    # Velar (back of mouth)
    'k': 'REST', 'g': 'REST', 'ng': 'REST',
    
    # W sound
    'w': 'U',
}


def detect_language(text: str) -> str:
    """Определяет язык текста (ru или en)"""
    russian_chars = sum(1 for c in text.lower() if 'а' <= c <= 'я' or c == 'ё')
    english_chars = sum(1 for c in text.lower() if 'a' <= c <= 'z')
    
    return 'ru' if russian_chars > english_chars else 'en'


def text_to_visemes(text: str, duration: float = None) -> Tuple[List[str], float]:
    """
    Конвертирует текст в последовательность визем
    
    Args:
        text: Входной текст
        duration: Желаемая длительность анимации (если None - рассчитывается автоматически)
    
    Returns:
        Tuple[List[str], float]: (список визем, общая длительность)
    """
    if not text or not text.strip():
        return ['REST'], 0.5
    
    text = text.lower().strip()
    lang = detect_language(text)
    char_map = RUSSIAN_MAP if lang == 'ru' else ENGLISH_MAP
    
    visemes = []
    prev_viseme = None
    
    for char in text:
        if char in ' \t\n.,!?;:':
            # Пауза на знаках препинания
            if prev_viseme != 'REST':
                visemes.append('REST')
                prev_viseme = 'REST'
            continue
        
        viseme = char_map.get(char, None)
        
        if viseme and viseme != prev_viseme:
            visemes.append(viseme)
            prev_viseme = viseme
    
    # Всегда начинаем и заканчиваем с REST
    if not visemes or visemes[0] != 'REST':
        visemes.insert(0, 'REST')
    if visemes[-1] != 'REST':
        visemes.append('REST')
    
    # Рассчитываем длительность
    # ~100ms на визему, минимум 0.5s, максимум зависит от длины текста
    if duration is None:
        duration = max(0.5, min(len(visemes) * 0.08, len(text) * 0.05))
    
    return visemes, duration


def generate_viseme_dsl(text: str, duration: float = None) -> str:
    """
    Генерирует DSL команду VISEME для C++ обработчика
    
    Args:
        text: Входной текст
        duration: Желаемая длительность
    
    Returns:
        str: DSL команда, например 'VISEME "REST,A,E,O,REST" 2.0'
    """
    visemes, dur = text_to_visemes(text, duration)
    sequence = ','.join(visemes)
    return f'VISEME "{sequence}" {dur:.2f}'


def generate_full_dsl(text: str, emotion: str = 'calm', duration: float = None) -> List[str]:
    """
    Генерирует полный набор DSL команд для ответа ИИ
    
    Args:
        text: Текст ответа
        emotion: Определенная эмоция
        duration: Длительность (если None - автоматически)
    
    Returns:
        List[str]: Список DSL команд
    """
    visemes, vis_duration = text_to_visemes(text, duration)
    
    commands = []
    
    # 1. Эмоция
    commands.append(f'EMOTION {emotion} {vis_duration:.2f}')
    
    # 2. Визем последовательность (lip sync)
    sequence = ','.join(visemes)
    commands.append(f'VISEME "{sequence}" {vis_duration:.2f}')
    
    # 3. Движение щупалец в зависимости от эмоции
    if emotion in ['excited', 'happy']:
        commands.append(f'WIGGLE_ARMS fast {vis_duration:.2f}')
    elif emotion in ['sad', 'empathetic']:
        commands.append(f'GENTLE_WIGGLE {vis_duration:.2f}')
    elif emotion in ['angry']:
        commands.append(f'WIGGLE_ARMS fast {vis_duration * 0.5:.2f}')
    else:
        commands.append(f'WIGGLE_ARMS medium {vis_duration:.2f}')
    
    # 4. Мигание (в середине ответа)
    blink_time = vis_duration * 0.4
    commands.append(f'BLINK 0.15')
    
    return commands


# ============== QUICK VISEME LOOKUP ==============
# Для быстрого lip sync без полного анализа

QUICK_PATTERNS = {
    # Русские частые слоги
    'привет': ['REST', 'M', 'R', 'I', 'F', 'E', 'L', 'REST'],
    'здравствуйте': ['REST', 'S', 'L', 'R', 'A', 'F', 'S', 'L', 'F', 'U', 'I', 'L', 'E', 'REST'],
    'спасибо': ['REST', 'S', 'M', 'A', 'S', 'I', 'M', 'O', 'REST'],
    'пожалуйста': ['REST', 'M', 'O', 'SH', 'A', 'L', 'U', 'I', 'S', 'L', 'A', 'REST'],
    'да': ['REST', 'L', 'A', 'REST'],
    'нет': ['REST', 'L', 'E', 'L', 'REST'],
    'хорошо': ['REST', 'O', 'R', 'O', 'SH', 'O', 'REST'],
    
    # English common words
    'hello': ['REST', 'E', 'L', 'O', 'REST'],
    'hi': ['REST', 'A', 'I', 'REST'],
    'yes': ['REST', 'I', 'E', 'S', 'REST'],
    'no': ['REST', 'L', 'O', 'REST'],
    'thank': ['REST', 'TH', 'A', 'L', 'REST'],
    'please': ['REST', 'M', 'L', 'I', 'S', 'REST'],
    'okay': ['REST', 'O', 'REST', 'E', 'I', 'REST'],
}


def quick_viseme(word: str) -> List[str]:
    """Быстрый поиск визем для частых слов"""
    word_lower = word.lower().strip()
    if word_lower in QUICK_PATTERNS:
        return QUICK_PATTERNS[word_lower]
    return None


# ============== INTEGRATION WITH SENTIMENT ANALYZER ==============

def get_dsl_from_text(text: str) -> Tuple[str, List[str]]:
    """
    Обёртка для интеграции с существующим sentiment_analyzer
    Возвращает (emotion, dsl_commands) с lip sync
    """
    from sentiment_analyzer import get_emotion_from_text
    
    emotion = get_emotion_from_text(text)
    dsl_commands = generate_full_dsl(text, emotion)
    
    return emotion, dsl_commands


# ============== CLI TESTING ==============

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        text = ' '.join(sys.argv[1:])
    else:
        text = input("Enter text: ")
    
    print(f"\nInput: {text}")
    print(f"Language: {detect_language(text)}")
    
    visemes, duration = text_to_visemes(text)
    print(f"Visemes ({len(visemes)}): {visemes}")
    print(f"Duration: {duration:.2f}s")
    
    print(f"\nDSL command:")
    print(generate_viseme_dsl(text))
    
    print(f"\nFull DSL (with emotion 'happy'):")
    for cmd in generate_full_dsl(text, 'happy'):
        print(f"  {cmd}")
