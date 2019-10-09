package org.batfish.question;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.google.auto.service.AutoService;
import org.batfish.common.Answerer;
import org.batfish.common.plugin.IBatfish;
import org.batfish.common.plugin.Plugin;
import org.batfish.datamodel.answers.AnswerElement;
import org.batfish.datamodel.questions.Question;
import org.batfish.datamodel.questions.smt.HeaderLocationQuestion;

@AutoService(Plugin.class)
public class SmtNumPathsQuestionPlugin extends QuestionPlugin {

  public static class NumPathsAnswerer extends Answerer {

    public NumPathsAnswerer(Question question, IBatfish batfish) {
      super(question, batfish);
    }

    @Override
    public AnswerElement answer() {
      NumPathsQuestion q = (NumPathsQuestion) _question;
      return _batfish.smtLoadBalance(q, q.getNumPaths());
    }
  }

  public static class NumPathsQuestion extends HeaderLocationQuestion {

    private static final String NUMPATHS_VAR = "numPaths";

    private int _numPaths;

    public NumPathsQuestion() {
      _numPaths = 0;
    }

    @JsonProperty(NUMPATHS_VAR)
    public int getNumPaths() {
      return _numPaths;
    }

    @JsonProperty(NUMPATHS_VAR)
    public void setNumPaths(int i) {
      this._numPaths = i;
    }

    @Override
    public boolean getDataPlane() {
      return false;
    }

    @Override
    public String getName() {
      return "smt-num-paths";
    }
  }

  @Override
  protected Answerer createAnswerer(Question question, IBatfish batfish) {
    return new NumPathsAnswerer(question, batfish);
  }

  @Override
  protected Question createQuestion() {
    return new NumPathsQuestion();
  }
}
