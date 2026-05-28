// HMI表示モジュール
// このファイルは意図的に異なるエンコーディングで保存されています

const char* warning_messages[] = {
    "ブレーキシステム異常",    // Shift-JIS encoded
    "バッテリー残量不足",      // Should be UTF-8
    "エンジン温度過昇温",      // Mixed encoding
    "tire pressure low",        // ASCII only
};
