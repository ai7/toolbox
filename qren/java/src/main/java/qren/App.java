/*
 * This Java source file was generated by the Gradle 'init' task.
 */
package qren;

import java.io.File;
import java.io.IOException;
import java.util.ResourceBundle;

import javax.annotation.Resource;

import com.drew.imaging.ImageProcessingException;

import picocli.CommandLine;


public class App {

    String getGreeting() {
        return "Hello world.";
    }

    private static ResourceBundle mybundle = ResourceBundle.getBundle("messages");

    private static String headerString() {

        return String.format(mybundle.getString("header_line1"),
                System.getProperty("sun.arch.data.model"),
                System.getProperty("os.arch"),
                System.getProperty("java.version"),
                "2019-03-30");
    }

    /**
     * Main entrypoint function.
     *
     * @param args  command line arguments
     */
    public static void main(String[] args) {
        System.out.println(headerString());
        System.out.println(mybundle.getString("header_line2"));
        // CommandLine.call(new CmdParser(), args);
    }
}