#pragma once

#include <string>
#include <vector>
#include <map>

struct AnimationKeyframe {
    float time;
    std::string command;
    std::string param1;
    std::string param2;
    float duration;
};

struct OctopusState {
    std::string emotion;
    int eyebrow_pos;      // -1 (down), 0 (normal), 1 (up)
    float arm_wave[8];    // 0-1 for each arm
    bool blinking;
    float opacity;
};

class OctopusSMILGenerator {
public:
    OctopusSMILGenerator(int width = 240, int height = 240);
    
    std::string generateSMILAnimation(const std::string& timeline_dsl);
    std::string generateStaticEmotion(const std::string& emotion);
    
public:
    int canvas_width, canvas_height;
    std::map<std::string, std::string> emotion_colors;
    
    void initEmotionColors();
    std::string svgHeader();
    std::string svgFooter();
    
    std::string drawOctopusBase(const OctopusState& state);
    std::string drawHead(const OctopusState& state);
    std::string drawEyes(const OctopusState& state);
    std::string drawMouth(const OctopusState& state);
    std::string drawArms(const OctopusState& state);
    
    std::string emotionToEyeColor(const std::string& emotion);
    std::string emotionToMouthShape(const std::string& emotion);
    
    std::vector<AnimationKeyframe> parseTimeline(const std::string& dsl);
    OctopusState defaultState();
    OctopusState applyCommand(const OctopusState& state, const AnimationKeyframe& keyframe);
    
    std::string generateAnimateTag(const std::string& attr_name, 
                                    const std::string& from_val,
                                    const std::string& to_val,
                                    float begin_time,
                                    float duration);
};
class SVGModifier {
public:
    SVGModifier(const std::string& template_path);
    std::string modifyByDSL(const std::string& dsl);
    
public:
    std::string template_svg;
    std::string loadTemplate(const std::string& path);
    std::string generateMouthAnimate(const std::vector<AnimationKeyframe>& keyframes);
    std::string generateArmsAnimate(const std::vector<AnimationKeyframe>& keyframes);
    std::string generateEyebrowAnimate(const std::vector<AnimationKeyframe>& keyframes);
    std::string generateBlinkAnimate(const std::vector<AnimationKeyframe>& keyframes);
};
