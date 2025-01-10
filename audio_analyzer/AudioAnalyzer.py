from essentia.standard import MonoLoader, MetadataReader, TensorflowPredictEffnetDiscogs, TensorflowPredict2D, TensorflowPredictMusiCNN
import numpy as np
import json


class AudioAnalyzer:
    def __init__(self, file_path: str):
        self.__file_path = file_path
        self.__model_path = "./models/"
        self.__audio = self.__get_essentia_audio()

    @property
    def file_path(self):
        return self.__file_path

    def get_metadata(self) -> dict:
        """Get the metadata of a song

        Returns:
            dict: key and value of the metadata, e.g.{"album": "The Wildest!"}
        """
        metadata_pool = MetadataReader(filename=self.__file_path)()[7]
        metadata = {}

        for descriptor in metadata_pool.descriptorNames():
            key = descriptor.split(".")[-1]
            metadata[key] = metadata_pool[descriptor][0]
        return metadata

    def __get_essentia_audio(self) -> MonoLoader:
        """Load the file into an Essentia audio object

        Returns:
            MonoLoader: A MonoLoader object from essentia containing the audio
        """
        return MonoLoader(filename=self.__file_path,
                          sampleRate=16000, resampleQuality=4)()

    def __get_audio_feature_config(self, audio_feature: str) -> float:
        """Get the model name and graph filenames used for prediction of an audio feature

        Returns:
            float: _description_
        """
        with open("./data/audio_features_config.json", "r") as file:
            parameters = json.load(file)

        return parameters[audio_feature]

    def calculate_predictions(self, audio_feature: str) -> np.ndarray:
        """Calculate predictions of an audio feature
            https://essentia.upf.edu/models.html for meaning of values, e.g. first column happy, second column non_happy
        Args:
            audio_feature (str): Name of the audio feature, e.g. danceability

        Returns:
            np.ndarray: Predictions for each segment of a song
        """
        audio_config = self.__get_audio_feature_config(audio_feature)

        # Create embeddings based on pre-trained model (musiccn, effnet)
        match audio_config["model"]:
            case "musicnn":
                embedding_model = TensorflowPredictMusiCNN(
                    graphFilename=f"{self.__model_path}{audio_config['embedding_graph_filename']}", output="model/dense/BiasAdd")
            case "effnet":
                embedding_model = TensorflowPredictEffnetDiscogs(
                    graphFilename=f"{self.__model_path}{audio_config['embedding_graph_filename']}", output="PartitionedCall:1")

        embeddings = embedding_model(self.__audio)

        # Create predictions based on algorithm (regression, classifier)
        match audio_config["algorithm"]:
            case "regression":
                prediction_model = TensorflowPredict2D(
                    graphFilename=f"{self.__model_path}{audio_config['prediction_graph_filename']}", output="model/Identity")
            case "classifier":
                prediction_model = TensorflowPredict2D(
                    graphFilename=f"{self.__model_path}{audio_config['prediction_graph_filename']}", output="model/Softmax")

        predictions = prediction_model(embeddings)
        return predictions

    def calculate_prediction_metric(self, audio_feature: str, category: int = 0) -> tuple | float:
        """ Calculate a single prediction metric, 
            e.g. a ratio for classifiers (e.g. danceable/non-danceable ratio)
            or an average for regression

        Args:
            audio_feature (str): Name of the audio feature
            category (int, optional): Only relevant for classifier. 
                0 means the first category (e.g. danceable)
                1 means the second category (e.g. non-danceable)

        Returns:
            tuple | float: _description_
        """
        audio_config = self.__get_audio_feature_config(audio_feature)
        predictions = self.calculate_predictions(audio_feature)

        match audio_config["algorithm"]:
            case "regression":
                avg_predictions = np.mean(predictions, axis=0)
                return tuple(avg_predictions)
            case "classifier":
                count = np.sum(predictions[:, category] > 0.5)
                ratio = float(count / len(predictions))
                return ratio


if __name__ == "__main__":
    # Testing
    file_path = "/Users/ntruong/Documents/Personal/Programming/Projects/deejayssentia/music/happy_male_voice.mp3"
    audio_analyzer = AudioAnalyzer(file_path)
    print(audio_analyzer.calculate_prediction_metric("bright_dark"))