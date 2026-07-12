/**
 * SVG to Canvas Groups Converter
 * Парсит SVG, извлекает paths и группирует их по ID/классам
 *
 * Использование:
 * const converter = new SVGToGroupsConverter('path/to/octopus.svg');
 * const groups = await converter.parse();
 * console.log(groups); // { body: [0,1,2], leftEye: [10,11], ... }
 */

class SVGToGroupsConverter {
    constructor(svgPath) {
        this.svgPath = svgPath;
        this.paths = [];
        this.groups = {
            body: [],
            leftEye: [],
            rightEye: [],
            leftEyebrow: [],
            rightEyebrow: [],
            mouth: [],
            leftTentacle: [],
            rightTentacle: [],
            hair: [],
            other: []
        };
    }

    /**
     * Загружает SVG файл
     */
    async loadSVG() {
        try {
            const response = await fetch(this.svgPath);
            const text = await response.text();
            return new DOMParser().parseFromString(text, 'image/svg+xml');
        } catch (error) {
            console.error('Error loading SVG:', error);
            return null;
        }
    }

    /**
     * Нормализует имя для сравнения (lowercase, без спецсимволов)
     */
    normalize(str) {
        return str.toLowerCase().replace(/[\s_-]/g, '');
    }

    /**
     * Определяет группу по ID/классу/имени
     */
    getGroupFromElement(element) {
        const id = element.getAttribute('id') || '';
        const className = element.getAttribute('class') || '';
        const name = element.getAttribute('name') || '';

        const fullText = `${id} ${className} ${name}`.toLowerCase();
        const normalized = this.normalize(fullText);

        // Правила сопоставления (регулярные выражения)
        const rules = {
            body: [/body|torso|main|base|trunk|abdomen|head/],
            leftEye: [/left.*eye|eye.*left|l_eye|leye|eye_l/],
            rightEye: [/right.*eye|eye.*right|r_eye|reye|eye_r/],
            leftEyebrow: [/left.*brow|brow.*left|l_brow|lbrow|brow_l/],
            rightEyebrow: [/right.*brow|brow.*right|r_brow|rbrow|brow_r/],
            mouth: [/mouth|lips|lip|mouth_open|smile|tongue|jaw/],
            leftTentacle: [/left.*tentacle|tentacle.*left|arm_l|l_arm|l_tentacle|left_arm|left.*leg|leg.*left/],
            rightTentacle: [/right.*tentacle|tentacle.*right|arm_r|r_arm|r_tentacle|right_arm|right.*leg|leg.*right/],
            hair: [/hair|fringe|bangs|head_hair|top/]
        };

        // Проверяем каждое правило
        for (const [group, patterns] of Object.entries(rules)) {
            for (const pattern of patterns) {
                if (pattern.test(normalized)) {
                    return group;
                }
            }
        }

        return 'other';
    }

    /**
     * Извлекает все path элементы из SVG
     */
    extractPaths(svgDoc) {
        const paths = [];
        const elements = svgDoc.querySelectorAll('path');

        elements.forEach((element, index) => {
            const d = element.getAttribute('d');
            if (d) {
                paths.push({
                    index,
                    d,
                    id: element.getAttribute('id'),
                    class: element.getAttribute('class'),
                    fill: element.getAttribute('fill'),
                    stroke: element.getAttribute('stroke'),
                    strokeWidth: element.getAttribute('stroke-width'),
                    originalElement: element
                });
            }
        });

        return paths;
    }

    /**
     * Группирует пути по категориям
     */
    groupPaths(paths) {
        const groups = {
            body: [],
            leftEye: [],
            rightEye: [],
            leftEyebrow: [],
            rightEyebrow: [],
            mouth: [],
            leftTentacle: [],
            rightTentacle: [],
            hair: [],
            other: []
        };

        paths.forEach((path) => {
            const group = this.getGroupFromElement(path.originalElement);
            groups[group].push(path.index);
        });

        return groups;
    }

    /**
     * Основной метод парсинга
     */
    async parse() {
        console.log('📂 Loading SVG...');
        const svgDoc = await this.loadSVG();

        if (!svgDoc) {
            throw new Error('Failed to load SVG');
        }

        console.log('🔍 Extracting paths...');
        this.paths = this.extractPaths(svgDoc);
        console.log(`✅ Found ${this.paths.length} paths`);

        console.log('📊 Grouping paths...');
        this.groups = this.groupPaths(this.paths);

        // Выведем статистику
        console.log('\n=== GROUPING RESULTS ===');
        for (const [group, indices] of Object.entries(this.groups)) {
            if (indices.length > 0) {
                console.log(`${group}: ${indices.length} paths → indices: [${indices.join(', ')}]`);
            }
        }

        return {
            paths: this.paths,
            groups: this.groups,
            totalPaths: this.paths.length
        };
    }

    /**
     * Экспортирует в JSON
     */
    toJSON() {
        return JSON.stringify({
            paths: this.paths.map(p => ({
                index: p.index,
                d: p.d,
                id: p.id,
                fill: p.fill
            })),
            groups: this.groups,
            totalPaths: this.paths.length
        }, null, 2);
    }
}

console.log('✅ svg-to-groups.js loaded');
