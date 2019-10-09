package org.batfish.backend;

import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import java.io.File;
import java.io.IOException;
import java.nio.charset.Charset;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Collections;
import java.util.Map;
import java.util.SortedMap;
import java.util.TreeMap;
import java.util.UUID;
import org.apache.commons.collections4.map.LRUMap;
import org.batfish.common.BatfishException;
import org.batfish.common.BatfishLogger;
import org.batfish.common.BfConsts;
import org.batfish.common.NetworkSnapshot;
import org.batfish.common.util.CommonUtil;
import org.batfish.config.Settings;
import org.batfish.datamodel.Configuration;
import org.batfish.datamodel.DataPlane;
import org.batfish.datamodel.collections.BgpAdvertisementsByVrf;
import org.batfish.datamodel.collections.RoutesByVrf;
import org.batfish.dataplane.ibdp.IncrementalDataPlanePlugin;
import org.batfish.identifiers.FileBasedIdResolver;
import org.batfish.main.Batfish;

public class BatfishHelper {
  public static Batfish getBatfishFromTestrigText(Path containerPath, String[] configs) {
    String newContainerName = "c2t_" + UUID.randomUUID();
    Path containerDir = initContainer(containerPath, newContainerName);

    Map<String, String> configurationText = null;
    try {
      configurationText = getTextFromConfigs(configs);
    } catch (IOException e) {
      System.out.println("Could not read Configuration Files!");
      e.printStackTrace();
      return null;
    }

    Map<String, String> awsText = null;
    Map<String, String> bgpTablesText = null;
    Map<String, String> hostsText = null;
    Map<String, String> iptablesFilesText = null;
    Map<String, String> routingTablesText = null;

    Settings settings = new Settings(new String[] {});

    settings.setLogger(new BatfishLogger("debug", false));
    settings.setDisableUnrecognized(true);
    settings.setHaltOnConvertError(true);
    settings.setHaltOnParseError(true);
    settings.setThrowOnLexerError(true);
    settings.setThrowOnParserError(true);
    settings.setVerboseParse(true);

    settings.setStorageBase(containerPath);

    settings.setContainer(newContainerName);
    settings.setTestrig("tempSnapshotId");
    settings.setSnapshotName("tempSnapshot");

    Batfish.initTestrigSettings(settings);

    Path testrigPath = settings.getBaseTestrigSettings().getInputPath();
    settings.getBaseTestrigSettings().getOutputPath().toFile().mkdirs();
    settings.setActiveTestrigSettings(settings.getBaseTestrigSettings());

    writeTemporaryTestrigFiles(configurationText, testrigPath.resolve(BfConsts.RELPATH_CONFIGURATIONS_DIR));
    writeTemporaryTestrigFiles(awsText, testrigPath.resolve(BfConsts.RELPATH_AWS_CONFIGS_DIR));
    writeTemporaryTestrigFiles(bgpTablesText, settings.getBaseTestrigSettings().getEnvironmentBgpTablesPath());
    writeTemporaryTestrigFiles(hostsText, testrigPath.resolve(BfConsts.RELPATH_HOST_CONFIGS_DIR));
    writeTemporaryTestrigFiles(iptablesFilesText, testrigPath.resolve("iptables"));
    writeTemporaryTestrigFiles(routingTablesText, settings.getBaseTestrigSettings().getEnvironmentRoutingTablesPath());

    Batfish batfish =
        new Batfish(
            settings,
            makeTestrigCache(),
            makeTestrigCache(),
            makeDataPlaneCache(),
            makeDataPlaneCache(),
            makeEnvBgpCache(),
            makeEnvRouteCache(),
            null,
            new TestFileBasedIdResolver(settings.getStorageBase()));

    registerDataPlanePlugins(batfish);

    return batfish;
  }

  public static Path initContainer(Path containerPath, String containerName) {
    Path containerDir = containerPath.resolve(containerName);

    if (Files.exists(containerDir)) {
      throw new BatfishException("Container '" + containerName + "' already exists!");
    }
    if (!containerDir.toFile().mkdirs()) {
      throw new BatfishException("failed to create directory '" + containerDir + "'");
    }

    return containerDir;
  }

  private static class TestFileBasedIdResolver extends FileBasedIdResolver {
    public TestFileBasedIdResolver(Path storageBase) {
      super(storageBase);
    }
  }

  private static void registerDataPlanePlugins(Batfish batfish) {
    IncrementalDataPlanePlugin ibdpPlugin = new IncrementalDataPlanePlugin();
    ibdpPlugin.initialize(batfish);
  }

  public static Map<String, String> getTextFromConfigs(String[] configurationNames) throws IOException {
    SortedMap<String, String> configurationTextMap = new TreeMap<>();
    for (String configName : configurationNames) {
      byte[] encoded = Files.readAllBytes(Paths.get(configName));
      String configurationText = new String(encoded, Charset.defaultCharset());
      configurationTextMap.put(new File(configName).getName(), configurationText);
    }
    return configurationTextMap;
  }

  private static void writeTemporaryTestrigFiles(Map<String, String> filesText, Path outputDirectory) {
    if (filesText != null) {
      filesText.forEach(
          (filename, text) -> {
            outputDirectory.toFile().mkdirs();
            CommonUtil.writeFile(outputDirectory.resolve(filename), text);
          });
    }
  }

  private static Cache<NetworkSnapshot, SortedMap<String, Configuration>> makeTestrigCache() {
    return CacheBuilder.newBuilder().softValues().maximumSize(5).build();
  }

  private static Map<NetworkSnapshot, SortedMap<String, BgpAdvertisementsByVrf>> makeEnvBgpCache() {
    return Collections.synchronizedMap(new LRUMap<>(4));
  }

  private static Map<NetworkSnapshot, SortedMap<String, RoutesByVrf>> makeEnvRouteCache() {
    return Collections.synchronizedMap(new LRUMap<>(4));
  }

  private static Cache<NetworkSnapshot, DataPlane> makeDataPlaneCache() {
    return CacheBuilder.newBuilder().softValues().maximumSize(2).build();
  }
}
