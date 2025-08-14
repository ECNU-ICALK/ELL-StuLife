"""
Test runner for precheck functionality
Run this script in campus_life_bench conda environment
"""

import sys
import os
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def main():
    """Main test runner function"""
    print("🧪 Precheck Functionality Test Runner")
    print("=" * 50)
    print("Environment: campus_life_bench conda environment")
    print("Test Location: LifelongAgentBench-main/tests")
    print("=" * 50)
    
    try:
        # Import and run the comprehensive precheck tests
        from test_precheck_functionality import run_precheck_tests
        
        print("🚀 Starting precheck functionality tests...")
        success = run_precheck_tests()
        
        if success:
            print("\n🎉 All precheck tests completed successfully!")
            print("✅ Precheck functionality is working correctly")
        else:
            print("\n⚠️ Some tests failed - check output above for details")
            print("❌ Precheck functionality may have issues")
        
        return success
        
    except ImportError as e:
        print(f"❌ Failed to import test modules: {e}")
        print("💡 Make sure you're in the campus_life_bench conda environment")
        print("💡 And that all dependencies are installed")
        return False
    
    except Exception as e:
        print(f"🚨 Unexpected error during testing: {e}")
        return False


def check_environment():
    """Check if we're in the correct environment"""
    print("🔍 Environment Check:")
    
    # Check Python version
    print(f"   Python version: {sys.version}")
    
    # Check conda environment
    conda_env = os.environ.get('CONDA_DEFAULT_ENV', 'unknown')
    print(f"   Conda environment: {conda_env}")
    
    if conda_env != 'campus_life_bench':
        print("⚠️ Warning: Not in 'campus_life_bench' environment")
        print("💡 Please activate the correct environment with:")
        print("   conda activate campus_life_bench")
    else:
        print("✅ Correct conda environment detected")
    
    # Check current directory
    current_path = Path.cwd()
    print(f"   Current directory: {current_path}")
    
    # Check if we're in tests directory
    if current_path.name != 'tests':
        print("💡 Tip: Run this script from the tests directory for best results")
    
    print()


if __name__ == "__main__":
    print("🧪 Precheck Test Runner")
    print("=" * 50)
    
    # Check environment first
    check_environment()
    
    # Run tests
    success = main()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
