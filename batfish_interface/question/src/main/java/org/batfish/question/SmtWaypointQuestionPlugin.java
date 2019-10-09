package org.batfish.question;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.google.auto.service.AutoService;
import java.util.ArrayList;
import java.util.List;
import org.batfish.common.Answerer;
import org.batfish.common.plugin.IBatfish;
import org.batfish.common.plugin.Plugin;
import org.batfish.datamodel.answers.AnswerElement;
import org.batfish.datamodel.questions.Question;
import org.batfish.datamodel.questions.smt.HeaderLocationQuestion;

@AutoService(Plugin.class)
public class SmtWaypointQuestionPlugin extends QuestionPlugin {

  public static class WaypointsAnswerer extends Answerer {

    public WaypointsAnswerer(Question question, IBatfish batfish) {
      super(question, batfish);
    }

    @Override
    public AnswerElement answer() {
      WaypointsQuestion q = (WaypointsQuestion) _question;
      return _batfish.smtReachability(q);
    }
  }

  public static class WaypointsQuestion extends HeaderLocationQuestion {

    private static final String WAYPOINTS_VAR = "waypoints";

    private ArrayList<String> _waypoints;

    public WaypointsQuestion() {
      _waypoints = new ArrayList<String>();
    }

    @JsonProperty(WAYPOINTS_VAR)
    public List<String> getWaypoints() {
      return _waypoints;
    }

    @JsonProperty(WAYPOINTS_VAR)
    public void setWaypoints(ArrayList<String> waypoints) {
      this._waypoints = waypoints;
    }

    @JsonProperty(WAYPOINTS_VAR)
    public void addWaypoint(String e) {
      this._waypoints.add(e);
    }

    @Override
    public boolean getDataPlane() {
      return false;
    }

    @Override
    public String getName() {
      return "smt-waypoints";
    }
  }

  @Override
  protected Answerer createAnswerer(Question question, IBatfish batfish) {
    return new WaypointsAnswerer(question, batfish);
  }

  @Override
  protected Question createQuestion() {
    return new WaypointsQuestion();
  }
}
