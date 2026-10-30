import { useVideoPlayer, VideoView } from 'expo-video';
import { StyleSheet, View } from 'react-native';

const campfire = require('../../assets/video/campfire.mp4');

export default function CampfireBackground() {
  const player = useVideoPlayer(campfire, (p) => {
    p.loop = true;
    p.muted = true;
    p.play();
  });

  return (
    <>
      <VideoView
        style={StyleSheet.absoluteFill}
        player={player}
        contentFit="cover"
        nativeControls={false}
      />
      <View style={styles.dim} />
    </>
  );
}

const styles = StyleSheet.create({
  // 글씨가 잘 보이도록 영상을 살짝 어둡게
  dim: {
    ...StyleSheet.absoluteFill,
    backgroundColor: 'rgba(0, 0, 0, 0.45)',
  },
});
