import * as React from "react";
import { get as _get } from "lodash";
import GlobalAppContext from "./GlobalAppContext";

export type PinRecordingModalProps = {
  recordingToPin?: Listen;
  isCurrentUser: Boolean;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

export interface PinRecordingModalState {
  blurbContent?: string;
}

export default class PinRecordingModals extends React.Component<
  PinRecordingModalProps,
  PinRecordingModalState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;
  private maxBlurbContentLength = 250;

  constructor(props: PinRecordingModalProps) {
    super(props);
    this.state = { blurbContent: "" };
  }

  handleError = (error: string | Error, title?: string): void => {
    const { newAlert } = this.props;
    if (!error) {
      return;
    }
    newAlert(
      "danger",
      title || "Error",
      typeof error === "object" ? error.message : error
    );
  };

  handleBlurbInputChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    event.preventDefault();
    const input = event.target.value.replace(/\s\s+/g, " "); // remove line breaks and
    if (input.length > this.maxBlurbContentLength) {
      return;
    }
    console.log(input.length);
    this.setState({ blurbContent: input });
  };

  submitPinRecording = async (event: React.SyntheticEvent) => {
    event.preventDefault();
    const { recordingToPin, isCurrentUser, newAlert } = this.props;
    const { blurbContent } = this.state;
    const { APIService, currentUser } = this.context;

    if (isCurrentUser && currentUser?.auth_token) {
      const recordingMBID = _get(
        recordingToPin,
        "track_metadata.additional_info.recording_msid"
      );
      try {
        const status = await APIService.submitPinRecording(
          currentUser.auth_token,
          recordingMBID,
          blurbContent || null
        );
        this.setState({ blurbContent: "" });
        if (status === 200) {
          newAlert(
            "success",
            `You pinned a recording!`,
            `${recordingToPin?.track_metadata.artist_name} - ${recordingToPin?.track_metadata.track_name}`
          );
        }
      } catch (error) {
        this.handleError(error, "Error while pinning recording");
      }
    }
  };

  render() {
    const { recordingToPin } = this.props;
    const { blurbContent } = this.state;
    const track_name = recordingToPin?.track_metadata?.track_name;
    const artist_name = recordingToPin?.track_metadata?.artist_name;

    return (
      <div
        className="modal fade"
        id="PinRecordingModal"
        tabIndex={-1}
        role="dialog"
        aria-labelledby="PinRecordingModalLabel"
        data-backdrop="static"
      >
        <div className="modal-dialog" role="document">
          <form className="modal-content">
            <div className="modal-header">
              <button
                type="button"
                className="close"
                data-dismiss="modal"
                aria-label="Close"
              >
                <span aria-hidden="true">&times;</span>
              </button>
              <h4 className="modal-title" id="PinRecordingModalLabel">
                Pin This Recording to Your Profile
              </h4>
            </div>
            <div className="modal-body">
              <p>
                Why are you pinning{" "}
                <b>
                  {" "}
                  {track_name} - {artist_name}
                </b>
                ? (Optional)
              </p>
              <div className="form-group">
                <textarea
                  className="form-control"
                  id="reason"
                  placeholder="Tell us why you love this recording!"
                  value={blurbContent}
                  name="reason"
                  onChange={this.handleBlurbInputChange}
                  rows={4}
                  style={{ resize: "vertical" }}
                  spellCheck="false"
                />
              </div>
              <small style={{ display: "block", textAlign: "right" }}>
                {blurbContent?.length} / {this.maxBlurbContentLength}
              </small>
              <small>
                Pinning this recording will replace any recording currently
                pinned. <br />
                <b>
                  {track_name} by {artist_name}
                </b>{" "}
                will be unpinned from your profile in one week.
              </small>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-default"
                data-dismiss="modal"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-success"
                onClick={this.submitPinRecording}
                data-dismiss="modal"
              >
                Pin
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }
}
