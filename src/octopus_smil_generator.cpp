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

// Mouth shapes based on template coordinates (mouth at y=110)
std::string OctopusSMILGenerator::emotionToMouthShape(const std::string& emotion) {
    if (emotion == "happy") {
        return "M 100 110 Q 120 130 140 110";  // Wide smile
    } else if (emotion == "sad") {
        return "M 100 115 Q 120 100 140 115";  // Frown
    } else if (emotion == "surprised") {
        return "M 110 105 Q 120 125 130 105";  // Open O shape
    } else if (emotion == "angry") {
        return "M 100 112 L 120 110 L 140 112"; // Tight line
    } else if (emotion == "confused") {
        return "M 100 112 Q 120 108 140 115";  // Wavy/uncertain
    } else if (emotion == "empathetic") {
        return "M 100 110 Q 120 118 140 110";  // Gentle curve
    } else if (emotion == "excited") {
        return "M 95 108 Q 120 135 145 108";   // Big smile
    }
    // calm/default
    return "M 100 110 Q 120 125 140 110";
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
        } else if (command == "VISEME") {
            // VISEME <sequence> <duration>
            // e.g. VISEME "REST,A,E,O,REST" 2.0
            cmd_stream >> kf.param1;  // viseme sequence
            cmd_stream >> kf.duration;
            if (kf.duration == 0) kf.duration = 1.0f;
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
                                                      float duration,
                                                      const std::string& fill) {
    std::ostringstream ss;
    ss << std::fixed << std::setprecision(2);
    ss << "<animate attributeName=\"" << attr_name << "\" "
       << "from=\"" << from_val << "\" to=\"" << to_val << "\" "
       << "begin=\"" << begin_time << "s\" dur=\"" << duration << "s\" "
       << "fill=\"" << fill << "\"/>";
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

// ============== SVGModifier Implementation ==============

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

// ============== VISEME Mouth Shapes (Lip Sync) ==============
// Based on template mouth position (y=110, x=100-140)

std::string SVGModifier::visemeToMouthPath(const std::string& viseme) {
    // 8 основных визем
    if (viseme == "REST" || viseme == "M" || viseme == "B" || viseme == "P") {
        // Рот закрыт - прямая линия
        return "M 100 110 Q 120 110 140 110";
    }
    if (viseme == "A" || viseme == "AA") {
        // Широко открыт (а, я)
        return "M 95 105 Q 120 140 145 105";
    }
    if (viseme == "E" || viseme == "EH") {
        // Широкая улыбка, приоткрыт (е, э)
        return "M 93 108 Q 120 125 147 108";
    }
    if (viseme == "I" || viseme == "IY") {
        // Узкая улыбка (и, й)
        return "M 102 110 Q 120 120 138 110";
    }
    if (viseme == "O" || viseme == "OW") {
        // Круглый рот (о, ё)
        return "M 105 105 Q 120 135 135 105";
    }
    if (viseme == "U" || viseme == "UW" || viseme == "W") {
        // Маленький круглый (у, ю, в)
        return "M 110 108 Q 120 125 130 108";
    }
    if (viseme == "F" || viseme == "V") {
        // Нижняя губа поджата (ф, в)
        return "M 100 115 Q 120 108 140 115";
    }
    if (viseme == "L" || viseme == "N" || viseme == "T" || viseme == "D") {
        // Слегка открыт (л, н, т, д)
        return "M 98 108 Q 120 122 142 108";
    }
    if (viseme == "S" || viseme == "Z") {
        // Зубы видны (с, з)
        return "M 100 110 Q 120 115 140 110";
    }
    if (viseme == "SH" || viseme == "CH") {
        // Губы вперед (ш, ч)
        return "M 108 108 Q 120 122 132 108";
    }
    if (viseme == "TH") {
        // Язык между зубов
        return "M 100 112 Q 120 118 140 112";
    }
    if (viseme == "R") {
        // Слегка округлен (р)
        return "M 103 108 Q 120 125 137 108";
    }
    
    // Default: neutral/closed
    return "M 100 110 Q 120 115 140 110";
}

std::string SVGModifier::generateMouthAnimate(const std::vector<AnimationKeyframe>& keyframes) {
    if (keyframes.empty()) return "";
    
    std::ostringstream ss;
    ss << std::fixed << std::setprecision(2);
    
    OctopusSMILGenerator gen;
    
    // Check if we have VISEME commands (lip sync mode)
    bool hasViseme = false;
    for (const auto& kf : keyframes) {
        if (kf.command == "VISEME") {
            hasViseme = true;
            break;
        }
    }
    
    if (hasViseme) {
        // ============ LIP SYNC MODE ============
        // VISEME command format: VISEME "A,E,I,O,U,REST" 2.0
        // Parse viseme sequence and generate smooth animation
        
        for (const auto& kf : keyframes) {
            if (kf.command == "VISEME") {
                ss << "      <animate id=\"mouth-anim\" attributeName=\"d\" values=\"";
                
                // Parse comma-separated viseme sequence
                std::string seq = kf.param1;
                // Remove quotes if present
                if (!seq.empty() && seq[0] == '"') seq = seq.substr(1);
                if (!seq.empty() && seq[seq.length()-1] == '"') seq = seq.substr(0, seq.length()-1);
                
                std::istringstream vss(seq);
                std::string viseme;
                bool first = true;
                int count = 0;
                
                while (std::getline(vss, viseme, ',')) {
                    // Trim whitespace
                    viseme.erase(0, viseme.find_first_not_of(" \t"));
                    viseme.erase(viseme.find_last_not_of(" \t") + 1);
                    
                    if (!first) ss << ";";
                    ss << visemeToMouthPath(viseme);
                    first = false;
                    count++;
                }
                
                // Calculate timing - each viseme gets equal time
                float per_viseme = (count > 0) ? kf.duration / count : kf.duration;
                
                ss << "\" begin=\"" << kf.time << "s\" dur=\"" << kf.duration 
                   << "s\" calcMode=\"spline\" keySplines=\"";
                
                // Smooth spline transitions between visemes
                for (int i = 0; i < count - 1; i++) {
                    if (i > 0) ss << ";";
                    ss << "0.4 0 0.6 1";  // ease-in-out
                }
                
                ss << "\" fill=\"freeze\"/>\n";
                break;  // Only first VISEME command
            }
        }
        
        return ss.str();
    }
    
    // ============ EMOTION MODE (fallback) ============
    // Use emotion-based mouth shapes
    
    std::vector<std::string> mouth_shapes;
    std::vector<float> times;
    float total_time = 0;
    
    for (const auto& kf : keyframes) {
        std::string shape;
        if (kf.command == "EMOTION") {
            shape = gen.emotionToMouthShape(kf.param1);
        } else if (kf.command == "THINKING") {
            shape = gen.emotionToMouthShape("confused");
        } else if (kf.command == "EMPATHY") {
            shape = gen.emotionToMouthShape("empathetic");
        } else if (kf.command == "ANTICIPATION") {
            shape = gen.emotionToMouthShape("excited");
        }
        
        if (!shape.empty()) {
            mouth_shapes.push_back(shape);
            times.push_back(total_time);
        }
        total_time += kf.duration;
    }
    
    if (mouth_shapes.empty()) {
        // No emotion commands - return idle animation
        ss << "      <animate id=\"mouth-anim\" attributeName=\"d\" "
           << "values=\"M 100 110 Q 120 125 140 110;M 100 110 Q 120 120 140 110;M 100 110 Q 120 125 140 110\" "
           << "begin=\"0s\" dur=\"3s\" repeatCount=\"indefinite\" calcMode=\"spline\" "
           << "keySplines=\"0.4 0 0.6 1;0.4 0 0.6 1\"/>\n";
        return ss.str();
    }
    
    ss << "      <animate id=\"mouth-anim\" attributeName=\"d\" values=\"";
    for (size_t i = 0; i < mouth_shapes.size(); i++) {
        if (i > 0) ss << ";";
        ss << mouth_shapes[i];
    }
    ss << "\" begin=\"0s\" dur=\"" << total_time << "s\" fill=\"freeze\" "
       << "calcMode=\"spline\" keySplines=\"";
    for (size_t i = 0; i < mouth_shapes.size() - 1; i++) {
        if (i > 0) ss << ";";
        ss << "0.4 0 0.6 1";
    }
    ss << "\"/>\n";
    
    return ss.str();
}

std::string SVGModifier::generateArmsAnimate(const std::vector<AnimationKeyframe>& keyframes) {
    std::ostringstream ss;
    ss << std::fixed << std::setprecision(2);
    
    float total_time = 0;
    for (const auto& kf : keyframes) {
        if (kf.command == "WIGGLE_ARMS" || kf.command == "ANTICIPATION" || kf.command == "GENTLE_WIGGLE") {
            float freq = 0.5f;
            float amplitude = 15.0f;
            
            if (kf.command == "WIGGLE_ARMS") {
                if (kf.param1 == "fast") {
                    freq = 0.25f;
                    amplitude = 20.0f;
                } else if (kf.param1 == "medium") {
                    freq = 0.4f;
                    amplitude = 15.0f;
                } else { // slow
                    freq = 0.8f;
                    amplitude = 10.0f;
                }
            } else if (kf.command == "GENTLE_WIGGLE") {
                freq = 1.2f;
                amplitude = 8.0f;
            }
            
            int repeat_count = std::max(1, (int)(kf.duration / freq));
            
            // Generate animation for each arm individually
            // Each arm has different phase offset for natural wave effect
            for (int arm = 0; arm < 8; arm++) {
                float phase_offset = (arm * 0.1f);  // Stagger start times
                float arm_amplitude = amplitude + (arm % 2) * 5;  // Alternate amplitude
                
                ss << "      <animateTransform xlink:href=\"#arm-" << arm << "\" "
                   << "attributeName=\"transform\" type=\"rotate\" "
                   << "values=\"0 120 120;" << arm_amplitude << " 120 120;" 
                   << (-arm_amplitude) << " 120 120;0 120 120\" "
                   << "begin=\"" << (total_time + phase_offset) << "s\" "
                   << "dur=\"" << freq << "s\" "
                   << "repeatCount=\"" << repeat_count << "\" "
                   << "calcMode=\"spline\" keySplines=\"0.4 0 0.6 1;0.4 0 0.6 1;0.4 0 0.6 1\"/>\n";
            }
            break;  // Only first wiggle command
        }
        total_time += kf.duration;
    }
    
    // If no wiggle command, add subtle idle animation
    if (ss.str().empty()) {
        for (int arm = 0; arm < 8; arm++) {
            float phase_offset = (arm * 0.3f);
            ss << "      <animateTransform xlink:href=\"#arm-" << arm << "\" "
               << "attributeName=\"transform\" type=\"rotate\" "
               << "values=\"0 120 120;5 120 120;-5 120 120;0 120 120\" "
               << "begin=\"" << phase_offset << "s\" dur=\"2s\" "
               << "repeatCount=\"indefinite\" "
               << "calcMode=\"spline\" keySplines=\"0.4 0 0.6 1;0.4 0 0.6 1;0.4 0 0.6 1\"/>\n";
        }
    }
    
    return ss.str();
}

std::string SVGModifier::generateEyebrowAnimate(const std::vector<AnimationKeyframe>& keyframes) {
    std::ostringstream ss;
    ss << std::fixed << std::setprecision(2);
    
    float current_time = 0;
    std::string base_left = "M 90 55 Q 100 50 110 55";
    std::string base_right = "M 130 55 Q 140 50 150 55";
    
    for (const auto& kf : keyframes) {
        if (kf.command == "EYEBROW" || kf.command == "THINKING" || 
            kf.command == "EMPATHY" || kf.command == "EMOTION") {
            
            std::string direction = kf.param1;
            if (kf.command == "THINKING") direction = "up";
            if (kf.command == "EMPATHY") direction = "down";
            if (kf.command == "EMOTION") {
                if (kf.param1 == "sad" || kf.param1 == "angry" || kf.param1 == "empathetic") {
                    direction = "down";
                } else if (kf.param1 == "confused" || kf.param1 == "surprised") {
                    direction = "up";
                } else {
                    direction = "normal";
                }
            }
            
            std::string left_target, right_target;
            
            if (direction == "up") {
                left_target = "M 90 48 Q 100 40 110 48";
                right_target = "M 130 48 Q 140 40 150 48";
            } else if (direction == "down") {
                left_target = "M 90 60 Q 100 65 110 58";  // Inner down (worried look)
                right_target = "M 130 58 Q 140 65 150 60";
            } else {
                left_target = base_left;
                right_target = base_right;
            }
            
            // Left eyebrow animation
            ss << "    <animate xlink:href=\"#left-eyebrow\" "
               << "attributeName=\"d\" "
               << "values=\"" << base_left << ";" << left_target << "\" "
               << "begin=\"" << current_time << "s\" dur=\"" << kf.duration << "s\" "
               << "fill=\"freeze\" calcMode=\"spline\" keySplines=\"0.4 0 0.6 1\"/>\n";
            
            // Right eyebrow animation
            ss << "    <animate xlink:href=\"#right-eyebrow\" "
               << "attributeName=\"d\" "
               << "values=\"" << base_right << ";" << right_target << "\" "
               << "begin=\"" << current_time << "s\" dur=\"" << kf.duration << "s\" "
               << "fill=\"freeze\" calcMode=\"spline\" keySplines=\"0.4 0 0.6 1\"/>\n";
            
            break;  // Only first eyebrow-affecting command
        }
        current_time += kf.duration;
    }
    
    return ss.str();
}

std::string SVGModifier::generateBlinkAnimate(const std::vector<AnimationKeyframe>& keyframes) {
    std::ostringstream ss;
    ss << std::fixed << std::setprecision(2);
    
    float current_time = 0;
    bool found_blink = false;
    float blink_duration = 0.15f;  // Quick blink
    
    for (const auto& kf : keyframes) {
        if (kf.command == "BLINK") {
            found_blink = true;
            blink_duration = std::min(kf.duration, 0.4f);  // Cap at 0.4s
            
            // Animate eye height via scaleY transform
            // Left eye blink
            ss << "    <animateTransform xlink:href=\"#left-eye-white\" "
               << "attributeName=\"transform\" type=\"scale\" "
               << "values=\"1 1;1 0.1;1 1\" "
               << "begin=\"" << current_time << "s\" dur=\"" << blink_duration << "s\" "
               << "additive=\"sum\" calcMode=\"spline\" "
               << "keySplines=\"0.4 0 0.6 1;0.4 0 0.6 1\"/>\n";
            
            ss << "    <animateTransform xlink:href=\"#left-eye-pupil\" "
               << "attributeName=\"transform\" type=\"scale\" "
               << "values=\"1 1;1 0.1;1 1\" "
               << "begin=\"" << current_time << "s\" dur=\"" << blink_duration << "s\" "
               << "additive=\"sum\" calcMode=\"spline\" "
               << "keySplines=\"0.4 0 0.6 1;0.4 0 0.6 1\"/>\n";
            
            // Right eye blink
            ss << "    <animateTransform xlink:href=\"#right-eye-white\" "
               << "attributeName=\"transform\" type=\"scale\" "
               << "values=\"1 1;1 0.1;1 1\" "
               << "begin=\"" << current_time << "s\" dur=\"" << blink_duration << "s\" "
               << "additive=\"sum\" calcMode=\"spline\" "
               << "keySplines=\"0.4 0 0.6 1;0.4 0 0.6 1\"/>\n";
            
            ss << "    <animateTransform xlink:href=\"#right-eye-pupil\" "
               << "attributeName=\"transform\" type=\"scale\" "
               << "values=\"1 1;1 0.1;1 1\" "
               << "begin=\"" << current_time << "s\" dur=\"" << blink_duration << "s\" "
               << "additive=\"sum\" calcMode=\"spline\" "
               << "keySplines=\"0.4 0 0.6 1;0.4 0 0.6 1\"/>\n";
            
            break;
        }
        current_time += kf.duration;
    }
    
    // Add periodic idle blink if no explicit BLINK command
    if (!found_blink) {
        ss << "    <animateTransform xlink:href=\"#left-eye-white\" "
           << "attributeName=\"transform\" type=\"scale\" "
           << "values=\"1 1;1 0.1;1 1\" "
           << "begin=\"2s\" dur=\"0.15s\" repeatCount=\"indefinite\" repeatDur=\"10s\" "
           << "additive=\"sum\" calcMode=\"spline\" "
           << "keySplines=\"0.4 0 0.6 1;0.4 0 0.6 1\"/>\n";
        
        ss << "    <animateTransform xlink:href=\"#left-eye-pupil\" "
           << "attributeName=\"transform\" type=\"scale\" "
           << "values=\"1 1;1 0.1;1 1\" "
           << "begin=\"2s\" dur=\"0.15s\" repeatCount=\"indefinite\" repeatDur=\"10s\" "
           << "additive=\"sum\" calcMode=\"spline\" "
           << "keySplines=\"0.4 0 0.6 1;0.4 0 0.6 1\"/>\n";
        
        ss << "    <animateTransform xlink:href=\"#right-eye-white\" "
           << "attributeName=\"transform\" type=\"scale\" "
           << "values=\"1 1;1 0.1;1 1\" "
           << "begin=\"2s\" dur=\"0.15s\" repeatCount=\"indefinite\" repeatDur=\"10s\" "
           << "additive=\"sum\" calcMode=\"spline\" "
           << "keySplines=\"0.4 0 0.6 1;0.4 0 0.6 1\"/>\n";
        
        ss << "    <animateTransform xlink:href=\"#right-eye-pupil\" "
           << "attributeName=\"transform\" type=\"scale\" "
           << "values=\"1 1;1 0.1;1 1\" "
           << "begin=\"2s\" dur=\"0.15s\" repeatCount=\"indefinite\" repeatDur=\"10s\" "
           << "additive=\"sum\" calcMode=\"spline\" "
           << "keySplines=\"0.4 0 0.6 1;0.4 0 0.6 1\"/>\n";
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
    
    // Replace blink animate placeholder
    std::string blink_anim = generateBlinkAnimate(keyframes);
    size_t blink_pos = result.find("<!--BLINK_ANIMATE_PLACEHOLDER-->");
    if (blink_pos != std::string::npos) {
        result.replace(blink_pos, 32, blink_anim);
    }
    
    // Replace eyebrow animate placeholder
    std::string eyebrow_anim = generateEyebrowAnimate(keyframes);
    size_t eyebrow_pos = result.find("<!--EYEBROW_ANIMATE_PLACEHOLDER-->");
    if (eyebrow_pos != std::string::npos) {
        result.replace(eyebrow_pos, 34, eyebrow_anim);
    }
    
    return result;
}
