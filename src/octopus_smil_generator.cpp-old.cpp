#include "octopus_smil_generator.h"
#include <sstream>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <iomanip>

OctopusSMILGenerator::OctopusSMILGenerator(int width, int height)
    : canvas_width(width), canvas_height(height) {
    initEmotionColors();
}

void OctopusSMILGenerator::initEmotionColors() {
    emotion_colors["happy"] = "#FFD700";
    emotion_colors["sad"] = "#4A90E2";
    emotion_colors["angry"] = "#E74C3C";
    emotion_colors["surprised"] = "#F39C12";
    emotion_colors["confused"] = "#9B59B6";
    emotion_colors["calm"] = "#27AE60";
    emotion_colors["excited"] = "#E91E63";
    emotion_colors["empathetic"] = "#3498DB";
}

std::string OctopusSMILGenerator::svgHeader() {
    std::ostringstream ss;
    ss << "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n";
    ss << "<svg width=\"" << canvas_width << "\" height=\"" << canvas_height 
       << "\" xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\">\n";
    ss << "  <defs>\n";
    ss << "    <style>\n";
    ss << "      .octopus-head { fill: #FF6B9D; stroke: #FF1493; stroke-width: 2; }\n";
    ss << "      .octopus-eye { fill: white; stroke: black; stroke-width: 1; }\n";
    ss << "      .octopus-pupil { fill: black; }\n";
    ss << "      .octopus-mouth { stroke: black; stroke-width: 2; fill: none; }\n";
    ss << "      .octopus-arm { stroke: #FF6B9D; stroke-width: 3; fill: none; stroke-linecap: round; }\n";
    ss << "    </style>\n";
    ss << "  </defs>\n";
    return ss.str();
}

std::string OctopusSMILGenerator::svgFooter() {
    return "</svg>\n";
}

std::string OctopusSMILGenerator::emotionToEyeColor(const std::string& emotion) {
    auto it = emotion_colors.find(emotion);
    if (it != emotion_colors.end()) {
        return it->second;
    }
    return "#FFD700";
}

std::string OctopusSMILGenerator::emotionToMouthShape(const std::string& emotion) {
    if (emotion == "happy") {
        return "M 100 140 Q 120 160 140 140";
    } else if (emotion == "sad") {
        return "M 100 140 Q 120 120 140 140";
    } else if (emotion == "surprised") {
        return "M 120 130 L 120 150";
    } else if (emotion == "angry") {
        return "M 100 140 L 140 140";
    } else if (emotion == "confused") {
        return "M 100 145 Q 120 130 140 145";
    } else if (emotion == "empathetic") {
        return "M 100 140 Q 120 145 140 140";
    }
    return "M 100 140 Q 120 160 140 140";
}

std::string OctopusSMILGenerator::drawHead(const OctopusState& state) {
    std::ostringstream ss;
    ss << "  <circle cx=\"120\" cy=\"80\" r=\"50\" class=\"octopus-head\"/>\n";
    return ss.str();
}

std::string OctopusSMILGenerator::drawEyes(const OctopusState& state) {
    std::ostringstream ss;
    ss << "  <circle cx=\"100\" cy=\"70\" r=\"8\" class=\"octopus-eye\"/>\n";
    ss << "  <circle cx=\"100\" cy=\"70\" r=\"4\" class=\"octopus-pupil\"/>\n";
    ss << "  <circle cx=\"140\" cy=\"70\" r=\"8\" class=\"octopus-eye\"/>\n";
    ss << "  <circle cx=\"140\" cy=\"70\" r=\"4\" class=\"octopus-pupil\"/>\n";
    return ss.str();
}

std::string OctopusSMILGenerator::drawMouth(const OctopusState& state) {
    std::ostringstream ss;
    std::string mouth_path = emotionToMouthShape(state.emotion);
    ss << "  <path d=\"" << mouth_path << "\" class=\"octopus-mouth\"/>\n";
    return ss.str();
}

std::string OctopusSMILGenerator::drawArms(const OctopusState& state) {
    std::ostringstream ss;
    float center_x = 120;
    float center_y = 120;
    float base_radius = 50;
    float arm_length = 70;
    
    for (int i = 0; i < 8; i++) {
        float angle = (i * M_PI * 2.0f) / 8.0f;
        float base_x = center_x + base_radius * cos(angle);
        float base_y = center_y + base_radius * sin(angle);
        float end_x = center_x + (base_radius + arm_length) * cos(angle);
        float end_y = center_y + (base_radius + arm_length) * sin(angle);
        
        ss << "  <path d=\"M " << base_x << " " << base_y 
           << " Q " << (base_x + end_x) / 2 << " " << (base_y + end_y) / 2 - 10
           << " " << end_x << " " << end_y 
           << "\" class=\"octopus-arm\"/>\n";
    }
    return ss.str();
}

std::string OctopusSMILGenerator::drawOctopusBase(const OctopusState& state) {
    std::ostringstream ss;
    ss << drawHead(state);
    ss << drawEyes(state);
    ss << drawMouth(state);
    ss << drawArms(state);
    return ss.str();
}

OctopusState OctopusSMILGenerator::defaultState() {
    OctopusState state;
    state.emotion = "calm";
    state.eyebrow_pos = 0;
    state.blinking = false;
    state.opacity = 1.0f;
    for (int i = 0; i < 8; i++) {
        state.arm_wave[i] = 0.0f;
    }
    return state;
}

std::vector<AnimationKeyframe> OctopusSMILGenerator::parseTimeline(const std::string& dsl) {
    std::vector<AnimationKeyframe> keyframes;
    std::istringstream iss(dsl);
    std::string line;
    float current_time = 0.0f;
    
    while (std::getline(iss, line)) {
        line.erase(0, line.find_first_not_of(" \t\r\n"));
        line.erase(line.find_last_not_of(" \t\r\n") + 1);
        
        if (line.empty() || line[0] == '#') continue;
        
        std::istringstream cmd_stream(line);
        std::string command;
        cmd_stream >> command;
        
        AnimationKeyframe kf;
        kf.time = current_time;
        kf.command = command;
        
        if (command == "EMOTION") {
            cmd_stream >> kf.param1;
            cmd_stream >> kf.duration;
            if (kf.duration == 0) kf.duration = 1.0f;
        } else if (command == "WIGGLE_ARMS") {
            cmd_stream >> kf.param1;
            cmd_stream >> kf.duration;
            if (kf.duration == 0) kf.duration = 1.0f;
        } else if (command == "BLINK") {
            cmd_stream >> kf.duration;
            if (kf.duration == 0) kf.duration = 0.3f;
        } else if (command == "THINKING") {
            cmd_stream >> kf.duration;
            if (kf.duration == 0) kf.duration = 1.5f;
        } else if (command == "ANTICIPATION") {
            cmd_stream >> kf.duration;
            if (kf.duration == 0) kf.duration = 2.0f;
        } else if (command == "EMPATHY") {
            cmd_stream >> kf.duration;
            if (kf.duration == 0) kf.duration = 2.0f;
        } else if (command == "EYEBROW") {
            cmd_stream >> kf.param1;
            cmd_stream >> kf.duration;
            if (kf.duration == 0) kf.duration = 0.5f;
        } else if (command == "GENTLE_WIGGLE") {
            cmd_stream >> kf.duration;
            if (kf.duration == 0) kf.duration = 3.0f;
        }
        
        keyframes.push_back(kf);
        current_time += kf.duration;
    }
    
    return keyframes;
}

OctopusState OctopusSMILGenerator::applyCommand(const OctopusState& state, const AnimationKeyframe& keyframe) {
    OctopusState new_state = state;
    
    if (keyframe.command == "EMOTION") {
        new_state.emotion = keyframe.param1;
    } else if (keyframe.command == "EYEBROW") {
        if (keyframe.param1 == "up") new_state.eyebrow_pos = 1;
        else if (keyframe.param1 == "down") new_state.eyebrow_pos = -1;
        else new_state.eyebrow_pos = 0;
    } else if (keyframe.command == "WIGGLE_ARMS") {
        for (int i = 0; i < 8; i++) {
            new_state.arm_wave[i] = 0.5f;
        }
    } else if (keyframe.command == "THINKING") {
        new_state.emotion = "confused";
        new_state.eyebrow_pos = 1;
    } else if (keyframe.command == "ANTICIPATION") {
        new_state.emotion = "excited";
        for (int i = 0; i < 8; i++) {
            new_state.arm_wave[i] = 0.3f;
        }
    } else if (keyframe.command == "EMPATHY") {
        new_state.emotion = "empathetic";
        new_state.eyebrow_pos = -1;
    }
    
    return new_state;
}

std::string OctopusSMILGenerator::generateAnimateTag(const std::string& attr_name,
                                                      const std::string& from_val,
                                                      const std::string& to_val,
                                                      float begin_time,
                                                      float duration) {
    std::ostringstream ss;
    ss << std::fixed << std::setprecision(2);
    ss << "    <animate attributeName=\"" << attr_name << "\" "
       << "from=\"" << from_val << "\" "
       << "to=\"" << to_val << "\" "
       << "begin=\"" << begin_time << "s\" "
       << "dur=\"" << duration << "s\" "
       << "fill=\"freeze\" />\n";
    return ss.str();
}

std::string OctopusSMILGenerator::generateSMILAnimation(const std::string& timeline_dsl) {
    std::ostringstream ss;
    ss << std::fixed << std::setprecision(2);
    ss << svgHeader();
    
    auto keyframes = parseTimeline(timeline_dsl);
    if (keyframes.empty()) {
        ss << drawOctopusBase(defaultState());
        ss << svgFooter();
        return ss.str();
    }
    
    // Build all states from keyframes
    std::vector<OctopusState> states;
    OctopusState state = defaultState();
    states.push_back(state);
    
    for (const auto& kf : keyframes) {
        state = applyCommand(state, kf);
        states.push_back(state);
    }
    
    float center_x = 120;
    float center_y = 120;
    float base_radius = 50;
    float arm_length = 70;
    
    // Main SVG group
    ss << "  <g id=\"octopus\">\n";
    
    // === HEAD ===
    ss << "    <circle id=\"head\" cx=\"120\" cy=\"80\" r=\"50\" class=\"octopus-head\"/>\n";
    
    // === EYES ===
    ss << "    <circle id=\"left-eye-white\" cx=\"100\" cy=\"70\" r=\"8\" class=\"octopus-eye\"/>\n";
    ss << "    <circle id=\"left-eye-pupil\" cx=\"100\" cy=\"70\" r=\"4\" class=\"octopus-pupil\"/>\n";
    ss << "    <circle id=\"right-eye-white\" cx=\"140\" cy=\"70\" r=\"8\" class=\"octopus-eye\"/>\n";
    ss << "    <circle id=\"right-eye-pupil\" cx=\"140\" cy=\"70\" r=\"4\" class=\"octopus-pupil\"/>\n";
    
    // === MOUTH ===
    ss << "    <path id=\"mouth\" d=\"M 100 140 Q 120 160 140 140\" class=\"octopus-mouth\">\n";
    ss << "      <animate id=\"mouth-anim\" "
       << "attributeName=\"d\" "
       << "values=\"";
    
    // Generate mouth animation path
    for (size_t i = 0; i < states.size(); i++) {
        ss << emotionToMouthShape(states[i].emotion);
        if (i < states.size() - 1) ss << ";";
    }
    
    float total_time = 0;
    for (const auto& kf : keyframes) {
        total_time += kf.duration;
    }
    
    ss << "\" "
       << "begin=\"0s\" dur=\"" << total_time << "s\" fill=\"freeze\" />\n";
    ss << "    </path>\n";
    
    // === ARMS ===
    for (int i = 0; i < 8; i++) {
        float angle = (i * M_PI * 2.0f) / 8.0f;
        float base_x = center_x + base_radius * cos(angle);
        float base_y = center_y + base_radius * sin(angle);
        float end_x = center_x + (base_radius + arm_length) * cos(angle);
        float end_y = center_y + (base_radius + arm_length) * sin(angle);
        
        ss << "    <path id=\"arm-" << i << "\" "
           << "d=\"M " << base_x << " " << base_y 
           << " Q " << (base_x + end_x) / 2 << " " << (base_y + end_y) / 2 - 10
           << " " << end_x << " " << end_y 
           << "\" class=\"octopus-arm\"/>\n";
    }
    
    ss << "  </g>\n";
    ss << svgFooter();
    return ss.str();
}

std::string OctopusSMILGenerator::generateStaticEmotion(const std::string& emotion) {
    std::ostringstream ss;
    ss << svgHeader();
    
    OctopusState state = defaultState();
    state.emotion = emotion;
    
    if (emotion == "happy" || emotion == "excited") {
        state.eyebrow_pos = 0;
    } else if (emotion == "sad" || emotion == "empathetic") {
        state.eyebrow_pos = -1;
    } else if (emotion == "confused" || emotion == "thinking") {
        state.eyebrow_pos = 1;
    } else if (emotion == "angry") {
        state.eyebrow_pos = -1;
    }
    
    ss << drawOctopusBase(state);
    ss << svgFooter();
    
    return ss.str();
}

#include <fstream>
#include <sstream>

SVGModifier::SVGModifier(const std::string& template_path) {
    template_svg = loadTemplate(template_path);
}

std::string SVGModifier::loadTemplate(const std::string& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        std::cerr << "Error: Cannot open template " << path << std::endl;
        return "";
    }
    std::stringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

std::string SVGModifier::generateMouthAnimate(const std::vector<AnimationKeyframe>& keyframes) {
    if (keyframes.empty()) return "";
    
    std::ostringstream ss;
    ss << std::fixed << std::setprecision(2);
    
    // Build mouth path values
    ss << "      <animate id=\"mouth-anim\" attributeName=\"d\" values=\"";
    
    std::string prev_emotion = "calm";
    float total_time = 0;
    OctopusSMILGenerator gen;
    
    for (size_t i = 0; i < keyframes.size(); i++) {
        if (keyframes[i].command == "EMOTION") {
            ss << gen.emotionToMouthShape(keyframes[i].param1);
            prev_emotion = keyframes[i].param1;
        } else if (keyframes[i].command == "THINKING") {
            ss << gen.emotionToMouthShape("confused");
        } else if (keyframes[i].command == "EMPATHY") {
            ss << gen.emotionToMouthShape("empathetic");
        } else if (keyframes[i].command == "ANTICIPATION") {
            ss << gen.emotionToMouthShape("excited");
        }
        
        if (i < keyframes.size() - 1) ss << ";";
        total_time += keyframes[i].duration;
    }
    
    ss << "\" begin=\"0s\" dur=\"" << total_time << "s\" fill=\"freeze\"/>\n";
    
    return ss.str();
}

std::string SVGModifier::generateArmsAnimate(const std::vector<AnimationKeyframe>& keyframes) {
    std::ostringstream ss;
    
    float total_time = 0;
    for (const auto& kf : keyframes) {
        if (kf.command == "WIGGLE_ARMS" || kf.command == "ANTICIPATION" || kf.command == "GENTLE_WIGGLE") {
            float freq = 0.5f;
            if (kf.command == "WIGGLE_ARMS") {
                freq = (kf.param1 == "fast") ? 0.3f : (kf.param1 == "medium") ? 0.5f : 1.0f;
            }
            
            ss << std::fixed << std::setprecision(2);
            ss << "      <animateTransform id=\"arms-wiggle\" attributeName=\"transform\" "
               << "type=\"rotate\" values=\"0;15;-15;0\" "
               << "begin=\"" << total_time << "s\" dur=\"" << freq << "s\" "
               << "repeatCount=\"" << (int)(kf.duration / freq) << "\" />\n";
            break;  // Only first wiggle
        }
        total_time += kf.duration;
    }
    
    return ss.str();
}

std::string SVGModifier::generateEyebrowAnimate(const std::vector<AnimationKeyframe>& keyframes) {
    std::ostringstream ss;
    
    float current_time = 0;
    for (const auto& kf : keyframes) {
        if (kf.command == "EYEBROW") {
            float to_y = (kf.param1 == "up") ? 35 : (kf.param1 == "down") ? 65 : 50;
            
            ss << std::fixed << std::setprecision(2);
            ss << "    <animate id=\"eyebrow-anim\" attributeName=\"d\" "
               << "values=\"M 90 50 Q 100 40 110 50;M 90 " << to_y << " Q 100 " << (to_y - 10) << " 110 " << to_y << "\""
               << " begin=\"" << current_time << "s\" dur=\"" << kf.duration << "s\" fill=\"freeze\"/>\n";
            break;
        }
        current_time += kf.duration;
    }
    
    return ss.str();
}

std::string SVGModifier::modifyByDSL(const std::string& dsl) {
    OctopusSMILGenerator gen;
    auto keyframes = gen.parseTimeline(dsl);
    
    std::string result = template_svg;
    
    // Replace mouth animate placeholder
    std::string mouth_anim = generateMouthAnimate(keyframes);
    size_t mouth_pos = result.find("<!--MOUTH_ANIMATE_PLACEHOLDER-->");
    if (mouth_pos != std::string::npos) {
        result.replace(mouth_pos, 33, mouth_anim);
    }
    
    // Replace arms animate placeholder
    std::string arms_anim = generateArmsAnimate(keyframes);
    size_t arms_pos = result.find("<!--ARMS_ANIMATE_PLACEHOLDER-->");
    if (arms_pos != std::string::npos) {
        result.replace(arms_pos, 31, arms_anim);
    }
    
    // Replace eyebrow animate placeholder
    // Replace blink animate placeholder
    std::string blink_anim = generateBlinkAnimate(keyframes);
    size_t blink_pos = result.find("<!--BLINK_ANIMATE_PLACEHOLDER-->");
    if (blink_pos != std::string::npos) {
        result.replace(blink_pos, 32, blink_anim);
    }
    std::string eyebrow_anim = generateEyebrowAnimate(keyframes);
    size_t eyebrow_pos = result.find("<!--EYEBROW_ANIMATE_PLACEHOLDER-->");
    if (eyebrow_pos != std::string::npos) {
        result.replace(eyebrow_pos, 34, eyebrow_anim);
    }
    
    return result;
}

std::string SVGModifier::generateBlinkAnimate(const std::vector<AnimationKeyframe>& keyframes) {
    std::ostringstream ss;
    
    float current_time = 0;
    for (const auto& kf : keyframes) {
        if (kf.command == "BLINK") {
            ss << std::fixed << std::setprecision(2);
            ss << "      <animate id=\"blink-anim\" attributeName=\"opacity\" "
               << "values=\"1;0.3;1\" "
               << "begin=\"" << current_time << "s\" dur=\"" << kf.duration << "s\" />\n";
            break;
        }
        current_time += kf.duration;
    }
    
    return ss.str();
}
