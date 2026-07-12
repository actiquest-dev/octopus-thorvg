#ifndef OCTOPUS_SMIL_GENERATOR_H
#define OCTOPUS_SMIL_GENERATOR_H

#include <string>
#include <vector>
#include <map>

// Animation keyframe structure
struct AnimationKeyframe {
    float time = 0.0f;
    float duration = 1.0f;
    std::string command;
    std::string param1;
    std::string param2;
};

// Octopus state structure
struct OctopusState {
    std::string emotion = "calm";
    int eyebrow_pos = 0;       // -1 = down, 0 = normal, 1 = up
    bool blinking = false;
    float opacity = 1.0f;
    float arm_wave[8] = {0};
};

// SMIL Generator class
class OctopusSMILGenerator {
public:
    OctopusSMILGenerator(int width = 240, int height = 240);
    
    // Static SVG generation
    std::string generateStaticEmotion(const std::string& emotion);
    
    // Timeline parsing
    std::vector<AnimationKeyframe> parseTimeline(const std::string& dsl);
    
    // State management
    OctopusState defaultState();
    OctopusState applyCommand(const OctopusState& state, const AnimationKeyframe& keyframe);
    
    // Emotion mappings
    std::string emotionToMouthShape(const std::string& emotion);
    std::string emotionToEyeColor(const std::string& emotion);
    
private:
    int canvas_width;
    int canvas_height;
    std::map<std::string, std::string> emotion_colors;
    
    void initEmotionColors();
    std::string svgHeader();
    std::string svgFooter();
    std::string drawHead(const OctopusState& state);
    std::string drawEyes(const OctopusState& state);
    std::string drawMouth(const OctopusState& state);
    std::string drawArms(const OctopusState& state);
    std::string drawOctopusBase(const OctopusState& state);
    std::string generateAnimateTag(const std::string& attr_name,
                                   const std::string& from_val,
                                   const std::string& to_val,
                                   float begin_time,
                                   float duration,
                                   const std::string& fill = "freeze");
};

// SVG Modifier class - modifies template with animations
class SVGModifier {
public:
    SVGModifier(const std::string& template_path);
    
    // Main modification function
    std::string modifyByDSL(const std::string& dsl);
    
private:
    std::string template_svg;
    
    std::string loadTemplate(const std::string& path);
    
    // Animation generators
    std::string generateMouthAnimate(const std::vector<AnimationKeyframe>& keyframes);
    std::string generateArmsAnimate(const std::vector<AnimationKeyframe>& keyframes);
    std::string generateEyebrowAnimate(const std::vector<AnimationKeyframe>& keyframes);
    std::string generateBlinkAnimate(const std::vector<AnimationKeyframe>& keyframes);
    
    // Viseme (lip sync) support
    std::string visemeToMouthPath(const std::string& viseme);
};

#endif // OCTOPUS_SMIL_GENERATOR_H
