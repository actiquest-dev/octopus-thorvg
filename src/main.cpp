#include "octopus_smil_generator.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>

int main(int argc, char* argv[]) {
    std::string dsl;
    std::string line;
    
    // Читай DSL из stdin (одна команда в строке)
    while (std::getline(std::cin, line)) {
        if (!line.empty()) {
            dsl += line + "\n";
        }
    }
    
    if (dsl.empty()) {
        std::cerr << "No DSL input\n";
        return 1;
    }
    
    SVGModifier modifier("svg/octopus_template.svg");
    std::string svg = modifier.modifyByDSL(dsl);
    
    size_t animate_count = 0;
    size_t pos = 0;
    while ((pos = svg.find("<animate", pos)) != std::string::npos) {
        animate_count++;
        pos++;
    }
    std::cout << "Total <animate> tags: " << animate_count << "\n";
    
    std::ofstream file("svg/octopus.svg");
    file << svg;
    file.close();
    
    return 0;
}
