#!/usr/bin/env python3
"""
Генерирует octopus_groups.js из SVG файла
Группирует paths по их назначению (body, eyes, mouth и т.д.)
"""

import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

# Правила группировки по атрибутам (если есть)
GROUP_RULES = {
    'body': [r'body|torso|main|base|trunk|abdomen|head'],
    'leftEye': [r'left.*eye|eye.*left|l_eye|leye|eye_l'],
    'rightEye': [r'right.*eye|eye.*right|r_eye|reye|eye_r'],
    'leftEyebrow': [r'left.*brow|brow.*left|l_brow|lbrow|brow_l'],
    'rightEyebrow': [r'right.*brow|brow.*right|r_brow|rbrow|brow_r'],
    'mouth': [r'mouth|lips|lip|mouth_open|smile|tongue|jaw'],
    'leftTentacle': [r'left.*tentacle|tentacle.*left|arm_l|l_arm|l_tentacle|left_arm|left.*leg|leg.*left'],
    'rightTentacle': [r'right.*tentacle|tentacle.*right|arm_r|r_arm|r_tentacle|right_arm|right.*leg|leg.*right'],
    'hair': [r'hair|fringe|bangs|head_hair|top'],
}

# SVG viewBox координаты
SVG_WIDTH = 2048
SVG_HEIGHT = 2048
SVG_CENTER_X = 1024
SVG_CENTER_Y = 1024

def normalize(text):
    """Нормализует текст для сравнения"""
    return re.sub(r'[\s_-]', '', text.lower())

def parse_svg_path(path_d):
    """Парсит SVG path и возвращает абсолютные координаты"""
    x, y = 0, 0
    xs, ys = [], []

    # Регулярное выражение для парсинга path команд
    path_re = r'([MmLlCcQqZzHhVv])([^MmLlCcQqZzHhVv]*)'

    for match in re.finditer(path_re, path_d):
        cmd = match.group(1)
        args_str = match.group(2).strip()

        # Извлекаем числа
        args = re.findall(r'-?\d+\.?\d*(?:[eE][-+]?\d+)?', args_str)
        nums = [float(arg) for arg in args]

        try:
            if cmd == 'M' and len(nums) >= 2:
                x, y = nums[0], nums[1]
                xs.append(x)
                ys.append(y)
            elif cmd == 'm' and len(nums) >= 2:
                x += nums[0]
                y += nums[1]
                xs.append(x)
                ys.append(y)
            elif cmd in 'Ll' and len(nums) >= 2:
                if cmd == 'L':
                    x, y = nums[0], nums[1]
                else:
                    x += nums[0]
                    y += nums[1]
                xs.append(x)
                ys.append(y)
            elif cmd in 'Cc' and len(nums) >= 6:
                # Bezier curve - берём последнюю точку
                if cmd == 'C':
                    x, y = nums[4], nums[5]
                else:
                    x += nums[4]
                    y += nums[5]
                xs.append(x)
                ys.append(y)
            elif cmd in 'Qq' and len(nums) >= 4:
                # Quadratic curve
                if cmd == 'Q':
                    x, y = nums[2], nums[3]
                else:
                    x += nums[2]
                    y += nums[3]
                xs.append(x)
                ys.append(y)
            elif cmd in 'Hh' and len(nums) >= 1:
                if cmd == 'H':
                    x = nums[0]
                else:
                    x += nums[0]
                xs.append(x)
                ys.append(y)
            elif cmd in 'Vv' and len(nums) >= 1:
                if cmd == 'V':
                    y = nums[0]
                else:
                    y += nums[0]
                xs.append(x)
                ys.append(y)
        except (IndexError, ValueError):
            pass

    if not xs or not ys:
        return None

    return {
        'min_x': min(xs),
        'max_x': max(xs),
        'min_y': min(ys),
        'max_y': max(ys),
        'avg_x': sum(xs) / len(xs),
        'avg_y': sum(ys) / len(ys),
        'width': max(xs) - min(xs),
        'height': max(ys) - min(ys),
    }

def normalize_path_to_absolute(path_d):
    """Конвертирует относительные path команды в абсолютные"""
    x, y = 0, 0
    result = []

    path_re = r'([MmLlCcQqZzHhVv])([^MmLlCcQqZzHhVv]*)'

    for match in re.finditer(path_re, path_d):
        cmd = match.group(1)
        args_str = match.group(2).strip()

        args = re.findall(r'-?\d+\.?\d*(?:[eE][-+]?\d+)?', args_str)
        nums = [float(arg) for arg in args]

        try:
            if cmd == 'M':
                x, y = nums[0], nums[1]
                result.append(f'M{x} {y}')
            elif cmd == 'm':
                x += nums[0]
                y += nums[1]
                result.append(f'M{x} {y}')
            elif cmd == 'L':
                x, y = nums[0], nums[1]
                result.append(f'L{x} {y}')
            elif cmd == 'l':
                x += nums[0]
                y += nums[1]
                result.append(f'L{x} {y}')
            elif cmd == 'C':
                result.append(f'C{nums[0]} {nums[1]} {nums[2]} {nums[3]} {nums[4]} {nums[5]}')
                x, y = nums[4], nums[5]
            elif cmd == 'c':
                c1x, c1y = x + nums[0], y + nums[1]
                c2x, c2y = x + nums[2], y + nums[3]
                x, y = x + nums[4], y + nums[5]
                result.append(f'C{c1x} {c1y} {c2x} {c2y} {x} {y}')
            elif cmd == 'Q':
                result.append(f'Q{nums[0]} {nums[1]} {nums[2]} {nums[3]}')
                x, y = nums[2], nums[3]
            elif cmd == 'q':
                cpx, cpy = x + nums[0], y + nums[1]
                x, y = x + nums[2], y + nums[3]
                result.append(f'Q{cpx} {cpy} {x} {y}')
            elif cmd == 'H':
                x = nums[0]
                result.append(f'L{x} {y}')
            elif cmd == 'h':
                x += nums[0]
                result.append(f'L{x} {y}')
            elif cmd == 'V':
                y = nums[0]
                result.append(f'L{x} {y}')
            elif cmd == 'v':
                y += nums[0]
                result.append(f'L{x} {y}')
            elif cmd in 'Zz':
                result.append('Z')
        except (IndexError, ValueError):
            pass

    return ''.join(result)

def extract_coordinates(path_d):
    """Извлекает координаты из SVG path"""
    return parse_svg_path(path_d)

def get_group(element_id, element_class, element_name='', geom=None):
    """Определяет группу элемента по атрибутам или геометрии"""
    # Сначала попробуем по атрибутам
    full_text = f"{element_id} {element_class} {element_name}".lower()
    normalized = normalize(full_text)

    for group, patterns in GROUP_RULES.items():
        for pattern in patterns:
            if re.search(pattern, normalized):
                return group

    # Если не нашли по атрибутам, анализируем геометрию
    if geom is None:
        return 'other'

    avg_x = geom['avg_x']
    avg_y = geom['avg_y']
    width = geom['width']
    height = geom['height']

    # Определим, левая или правая сторона (от центра)
    is_left = avg_x < SVG_CENTER_X - 100
    is_right = avg_x > SVG_CENTER_X + 100

    # Верхняя часть (глаза, брови) - примерно Y < 900
    if avg_y < 900:
        # Маленькие элементы в верхней части = глаза/брови
        if width < 200 and height < 200:
            if is_left:
                return 'leftEye' if height < 150 else 'leftEyebrow'
            elif is_right:
                return 'rightEye' if height < 150 else 'rightEyebrow'

    # Рот - примерно Y от 900 до 1150
    if 900 <= avg_y <= 1150:
        if width > 100 and height > 50:
            return 'mouth'

    # Большие боковые элементы = щупальца
    if (is_left or is_right) and (width > 300 or height > 300):
        return 'leftTentacle' if is_left else 'rightTentacle'

    # Остальное - тело
    return 'body'

def extract_paths_from_svg(svg_path):
    """Извлекает все path элементы из SVG"""
    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Пространство имён SVG
    ns = {'svg': 'http://www.w3.org/2000/svg'}

    paths = []
    for idx, path_elem in enumerate(root.findall('.//svg:path', ns)):
        d = path_elem.get('d', '')
        if d:
            # Нормализуем paths в абсолютные команды
            d_normalized = normalize_path_to_absolute(d)
            geom = extract_coordinates(d_normalized)
            paths.append({
                'index': idx,
                'd': d_normalized,  # Используем нормализованный path
                'id': path_elem.get('id', ''),
                'class': path_elem.get('class', ''),
                'fill': path_elem.get('fill', '#000000'),
                'stroke': path_elem.get('stroke', 'none'),
                'stroke-width': path_elem.get('stroke-width', '1'),
                'geom': geom,
            })

    return paths

def group_paths(paths):
    """Группирует пути по категориям"""
    groups = {
        'body': [],
        'leftEye': [],
        'rightEye': [],
        'leftEyebrow': [],
        'rightEyebrow': [],
        'mouth': [],
        'leftTentacle': [],
        'rightTentacle': [],
        'hair': [],
        'other': []
    }

    for path in paths:
        # Пытаемся определить группу по атрибутам или геометрии
        group = get_group(path['id'], path['class'], geom=path['geom'])
        groups[group].append(path['index'])

    return groups

def generate_groups_js(paths, groups):
    """Генерирует JavaScript код с группами"""
    code = '// Auto-generated octopus path groups\n'
    code += '// Generated by generate_octopus_groups.py\n\n'

    # Статистика
    code += '/**\n'
    code += f' * Total paths: {len(paths)}\n'
    for group, indices in groups.items():
        if indices:
            code += f' * {group}: {len(indices)} paths\n'
    code += ' */\n\n'

    # Индексы групп
    code += 'window.OCTOPUS_PATH_GROUPS = {\n'
    for group, indices in groups.items():
        if indices:
            code += f"    {group}: [{', '.join(map(str, indices))}],\n"
    code += '};\n\n'

    # Информация о путях
    code += 'window.OCTOPUS_PATH_INFO = [\n'
    for path in paths:
        code += f"    {{ index: {path['index']}, "
        code += f"id: '{path['id']}', "
        code += f"fill: '{path['fill']}' }},\n"
    code += '];\n'

    return code

def main():
    svg_path = Path('frontend/svg/octopus.svg')
    output_path = Path('frontend/octopus_groups.js')

    if not svg_path.exists():
        print(f"❌ SVG file not found: {svg_path}")
        return False

    print(f"📂 Loading SVG from {svg_path}...")
    paths = extract_paths_from_svg(svg_path)
    print(f"✅ Found {len(paths)} paths")

    print("📊 Grouping paths...")
    groups = group_paths(paths)

    # Выведем статистику
    print("\n=== GROUPING RESULTS ===")
    for group, indices in groups.items():
        if indices:
            print(f"{group}: {len(indices)} paths → {indices[:5]}{'...' if len(indices) > 5 else ''}")

    print(f"\n📝 Generating JavaScript...")
    code = generate_groups_js(paths, groups)

    print(f"💾 Writing to {output_path}...")
    output_path.write_text(code)

    print(f"✅ Done! Created {output_path}")
    print(f"\n📌 Now use in octopus_animator.js:")
    print(f"   window.OCTOPUS_PATH_GROUPS['mouth']  // Indices of mouth paths")
    print(f"   window.OCTOPUS_PATH_GROUPS['leftEye'] // Indices of left eye paths")

    return True

if __name__ == '__main__':
    main()
