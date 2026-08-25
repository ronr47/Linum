#!/usr/bin/env python3
import json
import os

class SpotDataTokenizer:
    """Fast localized parsing engine that maps characters or token blocks to unique tensor index limits."""
    def __init__(self):
        self.vocab = {"[PAD]": 0, "[UNK]": 1, "[BOS]": 2, "[EOS]": 3}
        self.inverse_vocab = {v: k for k, v in self.vocab.items()}
        
    def fit_on_text(self, text_data):
        """Extracts unique characters from the stream array to build structural dictionary bounds."""
        unique_chars = sorted(list(set(text_data)))
        for char in unique_chars:
            if char not in self.vocab:
                new_idx = len(self.vocab)
                self.vocab[char] = new_idx
                self.inverse_vocab[new_idx] = char
        print(f"📋 [TOKENIZER] Built vocabulary configuration. Total tokens: {len(self.vocab)}")

    def encode(self, text_string, max_len=128):
        """Converts raw data strings instantly into a numerical matrix vector map."""
        encoded = [self.vocab["[BOS]"]]
        for char in text_string:
            encoded.append(self.vocab.get(char, self.vocab["[UNK]"]))
        encoded.append(self.vocab["[EOS]"])
        
        # Absolute sequence normalization padding
        if len(encoded) < max_len:
            encoded += [self.vocab["[PAD]"]] * (max_len - len(encoded))
        else:
            encoded = encoded[:max_len]
        return encoded

    def decode(self, token_ids):
        """Reverses numerical matrices back to clear human text strings."""
        return "".join([self.inverse_vocab.get(t_id, "[UNK]") for t_id in token_ids if t_id > 3])

if __name__ == "__main__":
    print("⚡ [INIT] Running Tokenizer Validation Module...")
    tokenizer = SpotDataTokenizer()
    
    # Mock ingest sample mirroring what gets saved on the spot
    sample_payload = "{'flight': 'W8519', 'status': 'active', 'lat': -9.44, 'lng': 147.18}"
    
    tokenizer.fit_on_text(sample_payload)
    vector = tokenizer.encode(sample_payload, max_len=32)
    print(f"✅ Encoded Vector Stream Matrix: {vector}")
    print(f"✅ Decoded Back-Translation: {tokenizer.decode(vector)}")
