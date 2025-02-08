interface Greeting {
    fun greet(name: String): String
}

class Test : Greeting {
    private val prefix = "Hello"

    override fun greet(name: String): String {
        return "$prefix, $name!"
    }
}

fun main(args: Array<String>) {
    val greeter = Test()
    println(greeter.greet("World"))
}
