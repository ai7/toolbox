// class that handles command line parsing

package qren;

import java.io.File;
import java.util.concurrent.Callable;

import picocli.CommandLine;



@CommandLine.Command(name = "qren", mixinStandardHelpOptions = true,
        version = "qren 0.1", sortOptions = false, header =
        "Q-Rename 1.0.0 [Java, 2019-03-30]\n" +
                "(c) 2002-2019 by Raymond Chi, all rights reserved.\n")
public class CmdParser implements Callable<Void> {

    @CommandLine.Option(names = "-i", description = "Display/dump EXIF information in files")
    private boolean infoMode;

    @CommandLine.Option(names = "-r", description = "Rename files to YYYYMMDD_HHMMSS_NNNN[_tag].ext")
    private boolean renameMode;

    @CommandLine.Option(names = "-p", description = "Ask the user to confirm each file.")
    private boolean paramPrompt;

    @CommandLine.Option(names = "-n", description = "Do nothing. Simulate the operation.")
    private boolean paramSimulate;

    @CommandLine.Option(names = "-g", description = "Show configuration file content.")
    private boolean paramShowConfig;

    @CommandLine.Parameters(arity = "1..*", paramLabel = "FILE", description = "File(s) to process.")
    private File[] inputFiles;

    @Override
    public Void call() throws Exception {
        // your business logic goes here...
        if (infoMode) {
            System.out.println("running info mode");
        } else if (renameMode) {
            System.out.println("running rename mode");
        }

        return null;
    }

}
