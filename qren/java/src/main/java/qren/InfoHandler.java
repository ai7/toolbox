package qren;

import java.io.File;
import java.io.IOException;

import com.drew.imaging.ImageMetadataReader;
import com.drew.imaging.ImageProcessingException;
import com.drew.metadata.Directory;
import com.drew.metadata.Metadata;
import com.drew.metadata.Tag;


public class InfoHandler {

    private File[] inputFiles;

    public void run() {
        for (File f : inputFiles) {
            System.out.println(f.getAbsolutePath());
            try {
                image_detail(f);
            } catch (IOException e) {
                e.printStackTrace();
            } catch (ImageProcessingException e) {
                e.printStackTrace();
            }
        }
    }

    private void image_detail(File file) throws IOException, ImageProcessingException {

        Metadata metadata = ImageMetadataReader.readMetadata(file);

        for (Directory directory : metadata.getDirectories()) {
            for (Tag tag : directory.getTags()) {
                System.out.format("[%s] - %s = %s\n",
                        directory.getName(), tag.getTagName(), tag.getDescription());
            }
            if (directory.hasErrors()) {
                for (String error : directory.getErrors()) {
                    System.err.format("ERROR: %s", error);
                }
            }
        }

    }


}
