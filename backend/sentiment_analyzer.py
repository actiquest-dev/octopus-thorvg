#!/usr/bin/env python3
"""
Sentiment Analyzer with Lip Sync Integration
Определяет эмоцию из текста и генерирует DSL команды включая визем последовательность
"""

from typing import Tuple, List
from viseme_generator import text_to_visemes, generate_viseme_dsl

# ============== EMOTION KEYWORDS ==============

EMOTION_KEYWORDS = {
    'happy': {
        # Русский
        'рад', 'радость', 'счастлив', 'счастье', 'весело', 'веселье', 'отлично', 
        'замечательно', 'прекрасно', 'хорошо', 'супер', 'класс', 'круто', 'ура',
        'люблю', 'нравится', 'доволен', 'довольна', 'улыбка',
        # English
        'happy', 'joy', 'glad', 'great', 'wonderful', 'excellent', 'awesome',
        'love', 'like', 'pleased', 'delighted', 'fantastic', 'amazing', 'good',
        'nice', 'beautiful', 'smile', 'yay', 'yes'
    },
    'excited': {
        # Русский
        'вау', 'ого', 'круто', 'невероятно', 'потрясающе', 'офигеть', 'обалдеть',
        'восторг', 'восхищение', 'энергия', 'взволнован', 'возбужден', 'нетерпение',
        # English
        'wow', 'amazing', 'incredible', 'awesome', 'excited', 'thrilled', 
        'can\'t wait', 'pumped', 'stoked', 'fired up', 'fantastic'
    },
    'sad': {
        # Русский
        'грустно', 'грусть', 'печаль', 'печально', 'тоска', 'уныние', 'скучаю',
        'плохо', 'ужасно', 'расстроен', 'расстроена', 'плачу', 'слезы', 'больно',
        'одиноко', 'одинокий', 'несчастье', 'горе',
        # English
        'sad', 'unhappy', 'upset', 'depressed', 'down', 'blue', 'miserable',
        'cry', 'tears', 'hurt', 'pain', 'lonely', 'miss', 'sorry', 'bad'
    },
    'angry': {
        # Русский
        'злой', 'зла', 'злость', 'гнев', 'бесит', 'раздражает', 'ненавижу',
        'достало', 'надоело', 'ярость', 'возмущен', 'возмущена', 'негодование',
        # English
        'angry', 'mad', 'furious', 'hate', 'annoyed', 'irritated', 'frustrated',
        'rage', 'outraged', 'pissed', 'fed up'
    },
    'confused': {
        # Русский
        'не понимаю', 'непонятно', 'странно', 'запутался', 'запуталась', 
        'сложно', 'трудно', 'как так', 'почему', 'зачем', 'хмм', 'думаю',
        # English
        'confused', 'don\'t understand', 'unclear', 'strange', 'weird', 
        'puzzled', 'hmm', 'thinking', 'wonder', 'why', 'how come'
    },
    'surprised': {
        # Русский
        'удивлен', 'удивлена', 'неожиданно', 'вот это да', 'ничего себе',
        'серьезно', 'правда', 'не может быть', 'шок', 'шокирует',
        # English
        'surprised', 'unexpected', 'really', 'seriously', 'no way',
        'shocking', 'unbelievable', 'what', 'oh my'
    },
    'empathetic': {
        # Русский
        'понимаю', 'сочувствую', 'жаль', 'сожалею', 'держись', 'всё будет',
        'поддержка', 'помогу', 'вместе', 'не волнуйся',
        # English
        'understand', 'sorry to hear', 'sympathize', 'care', 'support',
        'here for you', 'help', 'together', 'don\'t worry'
    },
    'nervous': {
        # Русский
        'нервничаю', 'волнуюсь', 'беспокойно', 'страшно', 'боюсь', 
        'тревога', 'переживаю', 'стресс',
        # English
        'nervous', 'anxious', 'worried', 'scared', 'afraid', 'stress',
        'tense', 'uneasy'
    }
}


def get_emotion_from_text(text: str) -> str:
    """
    Определяет доминирующую эмоцию в тексте
    
    Args:
        text: Входной текст
    
    Returns:
        str: Название эмоции (happy, sad, angry, и т.д.)
    """
    if not text:
        return 'calm'
    
    text_lower = text.lower()
    
    # Подсчет совпадений для каждой эмоции
    scores = {}
    for emotion, keywords in EMOTION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        # Бонус за точные совпадения слов
        words = set(text_lower.split())
        score += sum(2 for kw in keywords if kw in words)
        scores[emotion] = score
    
    # Находим эмоцию с максимальным счетом
    max_score = max(scores.values())
    
    if max_score == 0:
        return 'calm'
    
    # Возвращаем первую эмоцию с максимальным счетом
    for emotion, score in scores.items():
        if score == max_score:
            return emotion
    
    return 'calm'


def get_dsl_from_text(text: str) -> Tuple[str, List[str]]:
    """
    Главная функция - определяет эмоцию и генерирует DSL команды с lip sync
    
    Args:
        text: Текст для анализа (обычно OUTPUT_TRANSCRIPTION от Gemini)
    
    Returns:
        Tuple[str, List[str]]: (эмоция, список DSL команд)
    """
    if not text or not text.strip():
        return 'calm', ['EMOTION calm 1.0', 'BLINK 0.2']
    
    # 1. Определяем эмоцию
    emotion = get_emotion_from_text(text)
    
    # 2. Генерируем визем последовательность для lip sync
    visemes, duration = text_to_visemes(text)
    viseme_sequence = ','.join(visemes)
    
    # 3. Формируем DSL команды
    dsl_commands = []
    
    # Эмоция
    dsl_commands.append(f'EMOTION {emotion} {duration:.2f}')
    
    # Lip sync
    dsl_commands.append(f'VISEME "{viseme_sequence}" {duration:.2f}')
    
    # Движение щупалец в зависимости от эмоции
    arm_cmd = get_arm_command(emotion, duration)
    dsl_commands.append(arm_cmd)
    
    # Брови в зависимости от эмоции
    eyebrow_cmd = get_eyebrow_command(emotion)
    if eyebrow_cmd:
        dsl_commands.append(eyebrow_cmd)
    
    # Мигание
    dsl_commands.append('BLINK 0.15')
    
    return emotion, dsl_commands


def get_arm_command(emotion: str, duration: float) -> str:
    """Возвращает команду для щупалец в зависимости от эмоции"""
    if emotion == 'excited':
        return f'WIGGLE_ARMS fast {duration:.2f}'
    elif emotion == 'happy':
        return f'WIGGLE_ARMS medium {duration:.2f}'
    elif emotion == 'angry':
        return f'WIGGLE_ARMS fast {duration * 0.7:.2f}'
    elif emotion in ['sad', 'empathetic']:
        return f'GENTLE_WIGGLE {duration:.2f}'
    elif emotion == 'nervous':
        return f'WIGGLE_ARMS fast {duration * 0.5:.2f}'
    elif emotion == 'confused':
        return f'WIGGLE_ARMS slow {duration:.2f}'
    else:
        return f'WIGGLE_ARMS medium {duration:.2f}'


def get_eyebrow_command(emotion: str) -> str:
    """Возвращает команду для бровей в зависимости от эмоции"""
    if emotion in ['confused', 'surprised']:
        return 'EYEBROW up 0.3'
    elif emotion in ['sad', 'angry', 'empathetic']:
        return 'EYEBROW down 0.3'
    return None


# ============== DIRECT EMOTION DSL (without lip sync) ==============

DSL_MAP_SIMPLE = {
    'happy': ['EMOTION happy 0.8', 'WIGGLE_ARMS medium 1.0', 'BLINK 0.3'],
    'excited': ['EMOTION excited 0.8', 'WIGGLE_ARMS fast 1.5', 'BLINK 0.2'],
    'sad': ['EMOTION sad 1.0', 'GENTLE_WIGGLE 2.0', 'EYEBROW down 0.4', 'BLINK 0.4'],
    'angry': ['EMOTION angry 0.8', 'WIGGLE_ARMS fast 0.8', 'EYEBROW down 0.25', 'BLINK 0.25'],
    'confused': ['EMOTION confused 1.0', 'THINKING 1.0', 'EYEBROW up 0.3', 'BLINK 0.3'],
    'surprised': ['EMOTION surprised 0.6', 'EYEBROW up 0.3', 'BLINK 0.2'],
    'empathetic': ['EMOTION empathetic 1.0', 'EMPATHY 1.5', 'EYEBROW down 0.35', 'BLINK 0.35'],
    'nervous': ['EMOTION nervous 0.9', 'WIGGLE_ARMS fast 0.8', 'EYEBROW down 0.3', 'BLINK 0.15'],
    'calm': ['EMOTION calm 1.0', 'WIGGLE_ARMS slow 1.5', 'BLINK 0.3'],
}


def get_simple_dsl(emotion: str) -> List[str]:
    """Возвращает простой DSL без lip sync (для быстрых реакций)"""
    return DSL_MAP_SIMPLE.get(emotion, DSL_MAP_SIMPLE['calm'])


# ============== CLI TESTING ==============

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        text = ' '.join(sys.argv[1:])
    else:
        text = input("Enter text: ")
    
    print(f"\nInput: {text}")
    
    emotion, dsl = get_dsl_from_text(text)
    
    print(f"Detected emotion: {emotion}")
    print(f"\nDSL commands:")
    for cmd in dsl:
        print(f"  {cmd}")
    
    print(f"\nDSL as string (for C++):")
    print("\\n".join(dsl))
