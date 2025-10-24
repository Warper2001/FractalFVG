using System;

namespace TestCompilation
{
    public class VolumeConfirmationLevel
    {
        public const int NONE = 0;
        public const int LOW = 1;
        public const int MEDIUM = 2;
        public const int HIGH = 3;
    }
    
    public class TestClass
    {
        public static void Main()
        {
            Console.WriteLine("C# compilation test passed");
        }
    }
}