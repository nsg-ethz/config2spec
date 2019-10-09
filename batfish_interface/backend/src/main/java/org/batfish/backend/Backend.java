package org.batfish.backend;

import static spark.Spark.*;

import java.io.File;
import java.io.IOException;
import java.nio.charset.Charset;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import java.util.Set;
import java.util.SortedMap;
import java.util.SortedSet;
import java.util.TreeSet;

import org.batfish.common.bdd.BDDPacket;
import org.batfish.common.BdpOscillationException;
import org.batfish.common.plugin.DataPlanePlugin.ComputeDataPlaneResult;

import org.batfish.config.Settings;
import org.batfish.datamodel.AbstractRoute;
import org.batfish.datamodel.Configuration;
import org.batfish.datamodel.DataPlane;
import org.batfish.datamodel.Edge;
import org.batfish.datamodel.Fib;
import org.batfish.datamodel.Interface;
import org.batfish.datamodel.InterfaceAddress;
import org.batfish.datamodel.IpAccessList;
import org.batfish.datamodel.IpAccessListLine;
import org.batfish.datamodel.LocalRoute;
import org.batfish.datamodel.Topology;
import org.batfish.datamodel.questions.smt.HeaderLocationQuestion;
import org.batfish.main.Batfish;
import org.batfish.question.SmtNumPathsQuestionPlugin.NumPathsQuestion;
import org.batfish.question.SmtReachabilityQuestionPlugin.ReachabilityQuestion;
import org.batfish.question.SmtWaypointQuestionPlugin.WaypointsQuestion;
import org.batfish.symbolic.smt.PropertyChecker;
import spark.Request;
import spark.Response;


public class Backend {
  private static Batfish batfish;
  private static Settings settings;
  private static Path scenarioPath;
  private static SortedMap<String, Configuration> configurations;
  private static int numDataplanes;

  public static void main(String[] args) {
    if (args.length > 0) {
      port(Integer.parseInt(args[0]));
    } else {
      port(8192);
    }


    // Configure Spark
    post("/run_query", (req, res) -> processQuery(req, res));

    post("/init_minesweeper", (req, res) -> initMinesweeper(req, res));

    post("/get_dataplane", (req, res) -> getDataplane(req, res));

    post("/get_topology", (req, res) -> getTopology(req, res));
  }

  private static String initMinesweeper(Request req, Response res) {
    // System.out.println("Request: " + req.body());
    // System.out.println("Response: " + res.toString());

    // long startTime = System.currentTimeMillis();

    String answer;
    Path basePath = null;
    Path containerPath = null;
    String path = "";
    String[] configs = null;

    List<String> initParameters = Arrays.asList(req.body().split(";"));

    for (String parameter : initParameters) {
      String[] item = parameter.split(":");
      if (item.length > 1) {
        if (item[0].equals("BasePath")) {
          basePath = Paths.get(item[1]);
          containerPath = basePath.resolve("containers/");
        } else if (item[0].equals("ConfigPath")) {
          path = item[1];
        } else if (item[0].equals("ConfigFiles")) {
          configs = item[1].split(",");
        }  else {
          System.out.println("Unknown Parameter: " + item[0] + " - " + item[1]);
        }
      }
    }

    // if all is good, create Batfish Environment
    if (basePath != null && containerPath != null && path != "" && configs != null) {
      String[] fullConfigs = new String[configs.length];
      for (int i = 0; i < configs.length; i++) {
        fullConfigs[i] = path + "/" + configs[i];
      }

      batfish = BatfishHelper.getBatfishFromTestrigText(containerPath, fullConfigs);
      settings = batfish.getSettings();
      scenarioPath = Paths.get(path).getParent();

      configurations = batfish.loadConfigurations();

      numDataplanes = 0;

      answer = "Success";
    } else {
      answer = "Failure";
    }

    // System.out.println("It took " + (System.currentTimeMillis() - startTime) + ".");

    return answer;
  }

  private static String processQuery(Request req, Response res) {
    // System.out.println("Request: " + req.body());
    // System.out.println("Response: " + res.toString());

    long startTime = System.currentTimeMillis();

    HeaderLocationQuestion question = mapRequestToQuestion(req.body());

    PropertyChecker p = new PropertyChecker(new BDDPacket(), batfish, settings);

    String answer = "";
    if (question instanceof ReachabilityQuestion) {
      answer = (p.checkReachability(question)).prettyPrint();
    } else if (question instanceof NumPathsQuestion) {
      int k = ((NumPathsQuestion) question).getNumPaths();
      answer = (p.checkLoadBalancingSimple(question, k)).prettyPrint();
    } else if (question instanceof WaypointsQuestion) {
      List<String> waypoints = ((WaypointsQuestion) question).getWaypoints();
      answer = (p.checkWaypoints(question, waypoints)).prettyPrint();
    }
    // System.out.println("Success: " + answer);
    // System.out.println("It took " + (System.currentTimeMillis() - startTime) + ".");

    return answer;
  }

  private static String getTopology(Request req, Response res) {
    // long startTime = System.currentTimeMillis();

    Topology topology = batfish.getEnvironmentTopology();

    // create a file containing all edges
    String fileNameTopology = "topology.txt";
    Path fileTopology = scenarioPath.resolve(fileNameTopology);
    File f1 = new File(fileTopology.toString());

    SortedSet<Edge> tmpEdges = topology.getEdges();

    ArrayList<String> edges = new ArrayList<>();
    for (Edge edge: tmpEdges) {
      edges.add(edge.toString());
      // System.out.println(edge.toString());
    }

    try {
      f1.createNewFile();
      Files.write(fileTopology, edges, Charset.forName("UTF-8"));
    } catch (IOException e) {
      System.out.println("IOException when trying to create and write to the file: " + fileNameTopology + "; " + e);
    }

    // create a file containing all interfaces
    String fileNameInterfaces = "interfaces.txt";
    Path fileInterfaces = scenarioPath.resolve(fileNameInterfaces);
    File f2 = new File(fileInterfaces.toString());

    ArrayList<String> interfaceEntries = new ArrayList<String>();
    Map<String, SortedSet<Edge>> nodeEdges = topology.getNodeEdges();
    for (String node : nodeEdges.keySet()) {
      interfaceEntries.add("# Router:" + node);
      Configuration routerConfig = configurations.get(node);

      Map<String, Interface> interfaces = routerConfig.getAllInterfaces();
      for (Map.Entry<String, Interface> entry : interfaces.entrySet()) {
        String intfName = entry.getKey();

        StringBuilder intfSb = new StringBuilder();

        Interface intf = entry.getValue();

        intfSb.append("## Interface:" + intfName);

        IpAccessList inFilter = intf.getIncomingFilter();
        if (inFilter != null) {
          intfSb.append(";IN:" + inFilter.getName());
        }

        IpAccessList outFilter = intf.getOutgoingFilter();
        if (outFilter != null) {
          intfSb.append(";OUT:" + outFilter.getName());
        }

        interfaceEntries.add(intfSb.toString());

        Set<InterfaceAddress> intfAdresses= intf.getAllAddresses();
        for (InterfaceAddress intfAddress : intfAdresses) {
          interfaceEntries.add(intfAddress.toString());
        }
      }
    }

    try {
      f2.createNewFile();
      Files.write(fileInterfaces, interfaceEntries, Charset.forName("UTF-8"));
    } catch (IOException e) {
      System.out.println(
          "IOException when trying to create and write to the file: " + fileNameInterfaces + "; " + e);
    }

    // creating a file containing all ACLs
    String fileNameAcl = "acls.txt";
    Path fileAcl = scenarioPath.resolve(fileNameAcl);
    File f3 = new File(fileAcl.toString());

    ArrayList<String> aclEntries = new ArrayList<String>();
    for (String node : nodeEdges.keySet()) {
      aclEntries.add("# Router:" + node);
      Configuration routerConfig = configurations.get(node);

      Map<String, IpAccessList> aclDefinitions = routerConfig.getIpAccessLists();
      for (Map.Entry<String, IpAccessList> entry : aclDefinitions.entrySet()) {
        String aclName = entry.getKey();
        IpAccessList acl = entry.getValue();
        List<IpAccessListLine> aclLines = acl.getLines();
        for (IpAccessListLine aclLine : aclLines) {
          aclEntries.add(aclName + ":" + aclLine.getName());
        }
      }
    }

    try {
      f3.createNewFile();
      Files.write(fileAcl, aclEntries, Charset.forName("UTF-8"));
    } catch (IOException e) {
      System.out.println("IOException when trying to create and write to the file: " + fileNameAcl + "; " + e);
    }

    // System.out.println("It took " + (System.currentTimeMillis() - startTime) + ".");
    return "TOPO:" + fileNameTopology + ";INTERFACES:" + fileNameInterfaces + ";ACL:" + fileNameAcl;
  }

  private static String getDataplane(Request req, Response res) {
    // long startTime = System.currentTimeMillis();

    // increase the number of dataplanes, decide on the filename and create directories if needed
    ++numDataplanes;

    Path fibPath = scenarioPath.resolve("fibs");
    new File(fibPath.toString()).mkdirs();

    String fileNameFib = "fib-" + numDataplanes + ".txt";

    Path fileFib = fibPath.resolve(fileNameFib);
    File f = new File(fileFib.toString());
    try {
      f.createNewFile();
      Files.write(fileFib, new ArrayList<String>(), Charset.forName("UTF-8"));
    } catch (IOException e) {
      System.out.println("IOException when trying to create the file: " + fileNameFib + "; " + e);
    }

    // init the environment
    Topology topology = batfish.getEnvironmentTopology();

    // make a copy of all the edges
    Map<String, SortedSet<Edge>> nodeEdges = topology.getNodeEdges();

    // compute the dataplane for the provided concrete environment, start by parsing and setting
    // the environment
    String request = req.body();

    TreeSet<Edge> blackListEdges = new TreeSet<Edge>();
    if (request.contains("EdgeBlacklist:")) {
      String[] envParameters = request.split(":");

      if (envParameters.length > 1) {
        String[] edges = envParameters[1].split(",");

        for (String edge : edges) {
          // System.out.println(edge);

          String[] nodes = edge.split("=");
          Set<Edge> tmpEdges1 = nodeEdges.get(nodes[0]);
          Set<Edge> tmpEdges2 = nodeEdges.get(nodes[1]);

          // add a check to see if the edges actually exist, it can happen that an invalid endpoint
          // is specified.
          TreeSet<Edge> intersection = new TreeSet<Edge>(tmpEdges1);
          intersection.retainAll(tmpEdges2);

          blackListEdges.addAll(intersection);
        }
      }

      // System.out.println("Blacklisted Edges: " + blackListEdges);

      // set the environment
      topology.prune(blackListEdges, null, null);
    }

    // compute the dataplane
    DataPlane dp = null;
    try {
      ComputeDataPlaneResult dpResult = batfish.getDataPlanePlugin().computeDataPlane(false, configurations, topology);
      dp = dpResult._dataPlane;
    } catch (BdpOscillationException e) {
      System.out.println(e + " for the following blacklisted edges: " + blackListEdges);
    }

    if (dp != null) {
      // get the FIBs for all nodes in the network
      Map<String, Map<String, Fib>> fibsData = dp.getFibs();

      // store the FIBs in a file - There is one FIB per router and VRF
      for (Map.Entry<String, Map<String, Fib>> entry: fibsData.entrySet()) {
        String router = entry.getKey();

        ArrayList<String> fibEntries = new ArrayList<String>();
        fibEntries.add("# Router:" + router);

        for (Map.Entry<String, Fib> entry2: entry.getValue().entrySet()) {
          String vrf = entry2.getKey();
          fibEntries.add("## VRF:" + vrf);

          Fib tmpFib = entry2.getValue();

          for (Map.Entry<String, Set<AbstractRoute>> fibEntry: tmpFib.getRoutesByNextHopInterface().entrySet()) {
            String nextHopInterface = fibEntry.getKey();

            for (AbstractRoute route : fibEntry.getValue()) {
              if (!(route instanceof LocalRoute)) {
                // TODO consider ACLs!!!!!
                // System.out.println("Router: " + router + "; " + route.getNetwork() + " -> " + nextHopInterface + " (" + route.getClass().getSimpleName() + ")");
                fibEntries.add(route.getNetwork() + ";" + nextHopInterface + ";" + route.getClass().getSimpleName());
              }
            }
          }
        }
        try {
          Files.write(fileFib, fibEntries, Charset.forName("UTF-8"), StandardOpenOption.APPEND);
        } catch (IOException e) {
          System.out.println("IOException when trying to write to file: " + fileNameFib + "; " + e);
        }
      }
    } else {
      return "ERROR";
    }

    // System.out.println("It took " + (System.currentTimeMillis() - startTime) + ".");

    return "FIB:" + fileNameFib;
  }

  private static HeaderLocationQuestion mapRequestToQuestion(String request) {
    List<String> queryParameters = Arrays.asList(request.split(";"));

    HeaderLocationQuestion question = null;

    if (request.contains("Type:reachability")) {
      question = new ReachabilityQuestion();
    } else if (request.contains("Type:loadbalancing")) {
      question = new NumPathsQuestion();
    } else if (request.contains("Type:waypoint")) {
      question = new WaypointsQuestion();
    } else {
      System.out.println("Unknown Question Type: " + request);
      return null;
    }

    for (String parameter : queryParameters) {
      String[] item = parameter.split(":");
      if (item.length > 1) {

        switch (item[0]) {
          case "Negate":
            question.setNegate(Boolean.parseBoolean(item[1]));
            break;
          case "IngressNodeRegex":
            question.setIngressNodeRegex(item[1]);
            break;
          case "FinalNodeRegex":
            question.setFinalNodeRegex(item[1]);
            break;
          case "FinalIfaceRegex":
            question.setFinalIfaceRegex(item[1]);
            break;
          case "MaxFailures":
            question.setFailures(Integer.parseInt(item[1]));
            break;
          case "Environment":
            question.setFailureEnvironment(item[1]);
            break;
          case "Waypoints":
            if (question instanceof WaypointsQuestion) {
              ArrayList<String> waypointList = new ArrayList<>(Arrays.asList(item[1].split(",")));

              // RB Added
              // System.out.println(waypointList);

              // reverse the list of waypoints to start with the one closest to the destination.
              Collections.reverse(waypointList);
              ((WaypointsQuestion) question).setWaypoints(waypointList);
            }
            break;
          case "NumPaths":
            if (question instanceof NumPathsQuestion) {
              ((NumPathsQuestion) question).setNumPaths(Integer.parseInt(item[1]));
            }
            break;
          case "Type":
            break;
          default:
            System.out.println("Unknown Parameter: " + item[0] + " - " + item[1]);
        }
      }
    }
    return question;
  }
}