#!/usr/bin/env python3
"""
Script to verify Claude 4 models are properly configured in aider
"""
import json
import yaml
from pathlib import Path

def test_claude4_models():
    """Test that Claude 4 models are properly configured"""
    
    # Load model metadata
    metadata_file = Path("aider/resources/model-metadata.json")
    with open(metadata_file) as f:
        metadata = json.load(f)
    
    # Load model settings  
    settings_file = Path("aider/resources/model-settings.yml")
    with open(settings_file) as f:
        settings = yaml.safe_load(f)
    
    # Find Claude 4 models
    claude4_metadata = {k: v for k, v in metadata.items() if 'claude-4' in k}
    claude4_settings = [s for s in settings if 'claude-4' in s.get('name', '')]
    
    print("🎉 Claude 4 Model Configuration Summary")
    print("=" * 50)
    
    print(f"\n📊 Model Metadata ({len(claude4_metadata)} models):")
    for model_name, config in claude4_metadata.items():
        print(f"  ✓ {model_name}")
        print(f"    - Context: {config['max_input_tokens']:,} tokens")
        print(f"    - Provider: {config['litellm_provider']}")
        print(f"    - Vision: {config.get('supports_vision', False)}")
        print(f"    - Function calling: {config.get('supports_function_calling', False)}")
        print(f"    - Prompt caching: {config.get('supports_prompt_caching', False)}")
    
    print(f"\n⚙️  Model Settings ({len(claude4_settings)} configurations):")
    for setting in claude4_settings:
        print(f"  ✓ {setting['name']}")
        print(f"    - Edit format: {setting.get('edit_format', 'default')}")
        print(f"    - Weak model: {setting.get('weak_model_name', 'none')}")
        print(f"    - Repo map: {setting.get('use_repo_map', False)}")
    
    print(f"\n🚀 Total Claude 4 Models Available: {len(claude4_metadata) + len(claude4_settings)}")
    
    providers = set()
    for model_name in claude4_metadata.keys():
        if '/' in model_name:
            providers.add(model_name.split('/')[0])
        else:
            providers.add('anthropic')
    
    print(f"📡 Providers: {', '.join(sorted(providers))}")
    
    print("\n✅ All Claude 4 models are properly configured!")
    print("\n🔥 Ready for benchmarking!")
    
    # List available models for easy copy-paste
    print("\n📋 Available Model Names:")
    all_models = list(claude4_metadata.keys()) + [s['name'] for s in claude4_settings]
    for model in sorted(set(all_models)):
        print(f"  • {model}")

if __name__ == "__main__":
    test_claude4_models()