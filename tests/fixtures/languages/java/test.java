public interface Greeting {
    String greet(String name);
}

public class Test implements Greeting {
    private String prefix = "Hello";

    public String greet(String name) {
        return prefix + ", " + name + "!";
    }

    public static void main(String[] args) {
        Test greeter = new Test();
        System.out.println(greeter.greet("World"));
    }
}
