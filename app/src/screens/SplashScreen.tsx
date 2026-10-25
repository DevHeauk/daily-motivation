import React, {useEffect, useRef} from 'react';
import {View, Text, Animated, StyleSheet} from 'react-native';
import {colors} from '../constants/colors';

interface SplashScreenProps {
  onFinish: () => void;
}

export function SplashScreen({onFinish}: SplashScreenProps) {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const subtitleFade = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.sequence([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 600,
        useNativeDriver: true,
      }),
      Animated.timing(subtitleFade, {
        toValue: 1,
        duration: 400,
        useNativeDriver: true,
      }),
      Animated.delay(800),
    ]).start(() => {
      onFinish();
    });
  }, [fadeAnim, subtitleFade, onFinish]);

  return (
    <View style={styles.container}>
      <Animated.View style={[styles.logoArea, {opacity: fadeAnim}]}>
        <Text style={styles.logoIcon}>&#x275D;</Text>
        <Text style={styles.logoText}>매일 동기부여</Text>
      </Animated.View>
      <Animated.Text style={[styles.subtitle, {opacity: subtitleFade}]}>
        하루 한 줄, 마음에 새기다
      </Animated.Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoArea: {
    alignItems: 'center',
    marginBottom: 16,
  },
  logoIcon: {
    fontSize: 48,
    color: colors.primary,
    marginBottom: 12,
  },
  logoText: {
    fontSize: 32,
    fontWeight: '700',
    color: colors.text,
    letterSpacing: 2,
  },
  subtitle: {
    fontSize: 14,
    color: colors.textSecondary,
    letterSpacing: 1,
  },
});
