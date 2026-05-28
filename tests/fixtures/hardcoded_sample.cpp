// Test C++ file with hardcoded strings
#include <iostream>

void greet() {
    std::cout << "你好世界" << std::endl;
    std::cout << "Hello" << std::endl;
    std::string msg = "エラーメッセージ";
    std::string ko = "안녕하세요";
    std::string safe = "ASCII only";
    // std::string comment = "注释";
}

void raw_strings() {
    std::string r = R"(This is raw)";
}
