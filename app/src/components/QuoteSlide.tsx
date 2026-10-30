import { useEffect, useRef } from 'react';
import { Animated, Easing, StyleSheet, Text, useWindowDimensions } from 'react-native';
import { Quote } from '../types';

type Props = {
  quote: Quote;
  // below: 화면 아래에서 올라오며 등장 (기본), above: 위에서 내려오며 등장 (이전 명언으로 돌아갈 때)
  from?: 'below' | 'above';
};

// 명언이 천천히 미끄러지며 나타나고, 이어서 저자가 드러난다
export default function QuoteSlide({ quote, from = 'below' }: Props) {
  const { height } = useWindowDimensions();
  const progress = useRef(new Animated.Value(0)).current;
  const authorOpacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    progress.setValue(0);
    authorOpacity.setValue(0);
    Animated.sequence([
      Animated.timing(progress, {
        toValue: 1,
        duration: 2600,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
      Animated.timing(authorOpacity, {
        toValue: 1,
        duration: 1000,
        useNativeDriver: true,
      }),
    ]).start();
  }, [quote, progress, authorOpacity]);

  const translateY = progress.interpolate({
    inputRange: [0, 1],
    outputRange: [from === 'below' ? height * 0.5 : -height * 0.5, 0],
  });

  return (
    <Animated.View style={[styles.container, { opacity: progress, transform: [{ translateY }] }]}>
      <Text style={styles.text}>{quote.text}</Text>
      <Animated.Text style={[styles.author, { opacity: authorOpacity }]}>
        — {quote.author}
      </Animated.Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 32,
  },
  text: {
    color: '#fff',
    fontSize: 24,
    lineHeight: 38,
    fontWeight: '500',
    textAlign: 'center',
    textShadowColor: 'rgba(0, 0, 0, 0.6)',
    textShadowRadius: 8,
  },
  author: {
    marginTop: 24,
    color: 'rgba(255, 255, 255, 0.8)',
    fontSize: 16,
    textAlign: 'center',
  },
});
